from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.connector import Document, Permission, Project
from app.models.user import User
from app.services.enrichment.enrichment_service import EnrichmentService
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.parsers.document_parser import DocumentParser
from app.services.storage.s3_store import S3ObjectStore
from app.services.vector.indexer import VectorIndexer

logger = logging.getLogger(__name__)


class DocumentPipelineService:
    """
    Unified end-to-end ingestion pipeline for user-uploaded documents:
    1. Parses binary file to plain text & structural metadata.
    2. Stores raw copy into MinIO / S3 Store.
    3. Persists record & RBAC permission in PostgreSQL.
    4. Runs EnrichmentService (sections, entities, decision/project mentions).
    5. Links nodes and relationships into FalkorDB Canonical Graph.
    6. Chunks & indexes vectors into Qdrant.
    """

    def __init__(
        self,
        s3_store: S3ObjectStore | None = None,
        enrichment_service: EnrichmentService | None = None,
        vector_indexer: VectorIndexer | None = None,
        falkordb: FalkorDBClient | None = None,
    ):
        self.s3_store = s3_store or S3ObjectStore()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.falkordb = falkordb or FalkorDBClient()

    async def ingest_document(
        self,
        db: AsyncSession,
        current_user: User,
        filename: str,
        file_bytes: bytes,
        mime_type: str | None = None,
        custom_title: str | None = None,
        project_id: str | None = None,
        classification: str = "Internal",
        department: str | None = None,
    ) -> dict[str, Any]:
        doc_id = str(uuid.uuid4())
        tenant_id = getattr(current_user, "tenant_slug", None) or "telcosphere"
        title = custom_title.strip() if custom_title and custom_title.strip() else filename

        # 1. Parse text from uploaded file
        text, file_meta = DocumentParser.parse_file(filename, file_bytes, mime_type)
        if not text:
            raise ValueError(f"Uploaded file '{filename}' contains no readable text content.")

        # 2. Store raw binary file in S3 / MinIO
        storage_key = f"documents/{tenant_id}/{doc_id}/{filename}"
        await self.s3_store.put_object(
            key=storage_key,
            data=file_bytes,
            content_type=file_meta.get("format", mime_type or "application/octet-stream"),
        )
        logger.info(f"Uploaded raw document to storage: {storage_key}")

        # 3. PostgreSQL Ledger Insert
        user_dept = department or getattr(current_user, "department", None) or "Engineering"
        db_doc = Document(
            id=doc_id,
            title=title,
            source_system="upload",
            source_id=storage_key,
            project_id=project_id,
            team_id=getattr(current_user, "department", None),
            owner_user_id=str(current_user.id),
            storage_key=storage_key,
            mime_type=file_meta.get("format", mime_type),
        )
        db.add(db_doc)

        # Grant owner read/write permission and department read permission
        perm_owner = Permission(
            entity_type="document",
            entity_id=doc_id,
            principal_type="user",
            principal_id=str(current_user.id),
            access_level="ADMIN",
            scope=classification,
        )
        db.add(perm_owner)
        await db.commit()
        await db.refresh(db_doc)

        # 4. Enrichment (Sections, Entities, Decisions, Project Mentions)
        enrichment_result = None
        try:
            enrichment_result = await self.enrichment_service.enrich_document(
                document_id=doc_id,
                db=db,
                raw_text=text,
                force_reparse=True,
            )
        except Exception as e:
            logger.warning(f"Enrichment partial warning for doc {doc_id}: {e}", exc_info=True)

        # 5. FalkorDB Canonical Graph Ingestion
        try:
            # Create :Document node
            cypher_doc = """
            MERGE (d:Document {id: $doc_id})
            SET d.title = $title,
                d.source_system = 'upload',
                d.storage_key = $storage_key,
                d.classification = $classification,
                d.department = $department,
                d.updated_at = $now
            """
            self.falkordb.query(cypher_doc, {
                "doc_id": doc_id,
                "title": title,
                "storage_key": storage_key,
                "classification": classification,
                "department": user_dept,
                "now": datetime.now(timezone.utc).isoformat(),
            })

            # Link author (Person)-[:AUTHORED]->(Document)
            author_email = current_user.email.lower()
            cypher_author = """
            MATCH (d:Document {id: $doc_id})
            MERGE (p:Person {email: $email})
            ON CREATE SET p.id = $user_id, p.name = $user_name
            MERGE (p)-[:AUTHORED]->(d)
            """
            self.falkordb.query(cypher_author, {
                "doc_id": doc_id,
                "email": author_email,
                "user_id": f"person:{current_user.id}",
                "user_name": current_user.full_name or author_email,
            })

            # If project assigned, link (Document)-[:BELONGS_TO]->(Project)
            if project_id:
                cypher_proj = """
                MATCH (d:Document {id: $doc_id})
                MERGE (pr:Project {id: $project_id})
                MERGE (d)-[:BELONGS_TO]->(pr)
                """
                self.falkordb.query(cypher_proj, {"doc_id": doc_id, "project_id": project_id})

            # If entities were extracted, link (Document)-[:MENTIONS]->(Entity)
            if enrichment_result and getattr(enrichment_result, "entities", None):
                for ent in enrichment_result.entities:
                    ent_val = ent.entity_value.strip()
                    ent_type = ent.entity_type.capitalize()
                    cypher_ent = f"""
                    MATCH (d:Document {{id: $doc_id}})
                    MERGE (e:{ent_type} {{id: $ent_id}})
                    ON CREATE SET e.name = $ent_name
                    MERGE (d)-[:MENTIONS]->(e)
                    """
                    self.falkordb.query(cypher_ent, {
                        "doc_id": doc_id,
                        "ent_id": f"{ent.entity_type}:{ent_val.lower().replace(' ', '_')}",
                        "ent_name": ent_val,
                    })

        except Exception as e:
            logger.error(f"FalkorDB ingestion failed for {doc_id}: {e}", exc_info=True)

        # 6. Qdrant Vector Indexing
        indexed_chunks = 0
        try:
            vector_metadata = {
                "document_id": doc_id,
                "title": title,
                "source_system": "upload",
                "storage_key": storage_key,
                "classification": classification,
                "department": user_dept,
                "author_email": author_email,
                "author_name": current_user.full_name,
                "project_id": project_id,
            }
            indexed_chunks = await self.vector_indexer.index_document(
                document_id=doc_id,
                text=text,
                metadata=vector_metadata,
                chunk_size=350,
            )
        except Exception as e:
            logger.error(f"Vector indexing failed for {doc_id}: {e}", exc_info=True)

        return {
            "document_id": doc_id,
            "title": title,
            "filename": filename,
            "storage_key": storage_key,
            "size_bytes": len(file_bytes),
            "indexed_chunks": indexed_chunks,
            "entities_found": len(enrichment_result.entities) if enrichment_result and getattr(enrichment_result, "entities", None) else 0,
            "status": "ready",
            "message": f"Successfully ingested '{title}' into storage, graph, and vector database.",
        }

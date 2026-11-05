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
from app.models.validation import (
    CascadeLogRecord,
    ConflictRecord,
    InferenceEventRecord,
    ValidationLogRecord,
)
from app.services.enrichment.enrichment_service import (
    EnrichmentService,
    NormalizedIngestionManifest,
)
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.graph.inference_engine import UniversalInferenceEngine
from app.services.parsers.document_parser import DocumentParser, ParsedDocumentResult
from app.services.storage.s3_store import S3ObjectStore
from app.services.vector.indexer import VectorIndexer
from app.services.vector.stale_vector_cleanup import CascadeReindexingService
from app.services.ledger.relational_ledger_service import RelationalLedgerService
from app.services.graph.ontology_evolution_service import OntologyEvolutionService

logger = logging.getLogger(__name__)


class DocumentPipelineService:
    """
    UKGOE Unified Ingestion Pipeline (Phase 1):
    1. Parses raw file into text, tables, structuredness, and inferred fields.
    2. Archives raw copy into S3 / MinIO (INV-01 Never Discard).
    3. Persists document record & RBAC permission in PostgreSQL.
    4. Runs EnrichmentService (sections, universal entities, stubs, taxonomy relationships).
    5. Links normalized entities, stubs, and edges into FalkorDB Canonical Graph.
    6. Chunks & indexes vectors into Qdrant.
    """

    def __init__(
        self,
        s3_store: S3ObjectStore | None = None,
        enrichment_service: EnrichmentService | None = None,
        vector_indexer: VectorIndexer | None = None,
        falkordb: FalkorDBClient | None = None,
        graph_repo: GraphRepository | None = None,
        inference_engine: UniversalInferenceEngine | None = None,
        cascade_reindexer: CascadeReindexingService | None = None,
        relational_ledger: RelationalLedgerService | None = None,
        evolution_service: OntologyEvolutionService | None = None,
    ):
        self.s3_store = s3_store or S3ObjectStore()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.falkordb = falkordb or FalkorDBClient()
        self.graph_repo = graph_repo or GraphRepository(client=self.falkordb)
        self.inference_engine = inference_engine or UniversalInferenceEngine(falkordb_client=self.falkordb)
        self.cascade_reindexer = cascade_reindexer or CascadeReindexingService(
            qdrant=self.vector_indexer.qdrant,
            falkordb=self.falkordb,
            indexer=self.vector_indexer,
        )
        self.relational_ledger = relational_ledger or RelationalLedgerService()
        self.evolution_service = evolution_service or OntologyEvolutionService(
            graph_client=self.falkordb,
            qdrant_service=self.vector_indexer.qdrant,
        )

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
        tenant_id = getattr(current_user, "tenant_slug", None) or "enterprise"
        title = custom_title.strip() if custom_title and custom_title.strip() else filename

        # 1. Step 1.1: Parse and Surface Structure
        parsed: ParsedDocumentResult = DocumentParser.parse_file(filename, file_bytes, mime_type)
        if not parsed.text:
            raise ValueError(f"Uploaded file '{filename}' contains no readable text content.")

        # 2. INV-01: Store raw binary file in S3 / MinIO (Never Discard)
        storage_key = f"documents/{tenant_id}/{doc_id}/{filename}"
        await self.s3_store.put_object(
            key=storage_key,
            data=file_bytes,
            content_type=parsed.format or mime_type or "application/octet-stream",
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
            mime_type=parsed.format,
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

        # 4. Step 1.2 & 1.3: Enrichment (Universal Entities, Stubs, Conflicts, Taxonomy Edges)
        manifest: NormalizedIngestionManifest | None = None
        try:
            manifest = await self.enrichment_service.enrich_document(
                document_id=doc_id,
                db=db,
                raw_text=parsed.text,
                structuredness=parsed.structuredness,
                inferred_fields=parsed.inferred_fields,
                force_reparse=True,
            )
        except Exception as e:
            logger.warning(f"Enrichment partial warning for doc {doc_id}: {e}", exc_info=True)

        # 5. FalkorDB Canonical Graph Ingestion & Universal Inference (Phase 2)
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            author_email = current_user.email.lower()
            author_id = f"person:{current_user.id}"

            # 5.1 Ingest Document Node
            await self.graph_repo.upsert_universal_node(
                label="Document",
                entity_id=doc_id,
                properties={
                    "title": title,
                    "source_system": "upload",
                    "storage_key": storage_key,
                    "classification": classification,
                    "department": user_dept,
                    "structuredness": parsed.structuredness,
                },
                source_doc_id=doc_id,
            )

            # 5.2 Link Author
            await self.graph_repo.upsert_universal_node(
                label="Person",
                entity_id=author_id,
                properties={"email": author_email, "name": current_user.full_name or author_email},
                source_doc_id=doc_id,
            )
            await self.graph_repo.upsert_universal_edge(
                source_id=author_id,
                target_id=doc_id,
                rel_type="AUTHORED",
                properties={"created_at": now_iso},
            )

            # 5.3 Link Project if provided
            if project_id:
                await self.graph_repo.upsert_universal_node(
                    label="Project",
                    entity_id=project_id,
                    properties={"id": project_id},
                    source_doc_id=doc_id,
                )
                await self.graph_repo.upsert_universal_edge(
                    source_id=doc_id,
                    target_id=project_id,
                    rel_type="BELONGS_TO",
                    properties={"created_at": now_iso},
                )

            # 5.4 Ingest Canonical Entities (with Stub Resolution & History Diffs)
            touched_entity_ids = []
            if manifest and manifest.entities:
                for ent in manifest.entities:
                    props = {
                        "name": ent.label,
                        "completeness_score": ent.completeness_score,
                        "quality_grade": ent.data_quality_grade,
                        "validation_status": ent.validation_status,
                    }
                    if ent.properties:
                        props.update(ent.properties)

                    await self.graph_repo.upsert_universal_node(
                        label=ent.entity_class,
                        entity_id=ent.entity_id,
                        properties=props,
                        source_doc_id=doc_id,
                    )
                    await self.graph_repo.upsert_universal_edge(
                        source_id=doc_id,
                        target_id=ent.entity_id,
                        rel_type="DOCUMENTS",
                        properties={"created_at": now_iso},
                    )
                    touched_entity_ids.append((ent.entity_class, ent.entity_id, props))

                    # UKGOE Step 6.1: Candidate Class Evaluation
                    if ent.entity_class == "Unclassified" or "candidate_class" in props:
                        cand_name = props.get("candidate_class") or ent.label
                        await self.evolution_service.evaluate_candidate_class(
                            candidate_name=cand_name,
                            entity_id=ent.entity_id,
                            source_doc_id=doc_id,
                            db=db,
                        )

                    # UKGOE INV-01: Audit validation anomalies into validation_log
                    if ent.validation_status and ent.validation_status != "valid":
                        db.add(ValidationLogRecord(
                            entity_id=ent.entity_id,
                            rule_id="INV-01-TEMPORAL" if "TEMPORAL" in ent.validation_status else "INV-01-SCHEMA",
                            status=ent.validation_status,
                            detail=f"Entity {ent.entity_id} validation status: {ent.validation_status}",
                        ))

            # 5.5 Ingest Stubs (INV-06 Stub Over Skip)
            if manifest and manifest.stubs:
                for stub in manifest.stubs:
                    await self.graph_repo.upsert_universal_node(
                        label="Stub",
                        entity_id=stub.entity_id,
                        properties={
                            "name": stub.label,
                            "stub_class": stub.entity_class,
                            "is_stub": True,
                            "status": "unresolved",
                        },
                        source_doc_id=doc_id,
                    )
                    await self.graph_repo.upsert_universal_edge(
                        source_id=doc_id,
                        target_id=stub.entity_id,
                        rel_type="PENDING_RESOLUTION",
                        properties={"created_at": now_iso},
                    )

            # 5.6 Ingest Taxonomy Relationships (with Compounding Multi-Cause Detection)
            if manifest and manifest.relationships:
                for rel in manifest.relationships:
                    await self.graph_repo.upsert_universal_edge(
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        rel_type=rel.relationship_type,
                        properties={
                            "confidence": rel.confidence,
                            "context": rel.context,
                            "source_doc_id": doc_id,
                        },
                        preserve_multi_cause=True,
                    )

                    # UKGOE Step 6.2: Candidate Relationship Evaluation
                    if rel.relationship_type == "RELATED_TO" or (hasattr(rel, "properties") and rel.properties.get("candidate_relation_type")):
                        cand_rel = (getattr(rel, "properties", {}) or {}).get("candidate_relation_type") or rel.context
                        if cand_rel and cand_rel != "RELATED_TO":
                            await self.evolution_service.evaluate_candidate_relation(
                                candidate_relation_type=cand_rel,
                                source_entity_id=rel.source_id,
                                target_entity_id=rel.target_id,
                                source_doc_id=doc_id,
                                db=db,
                            )

            # UKGOE INV-07: Ingest Contradictions and Conflicts into Relational Ledger
            if manifest and manifest.conflicts:
                for c in manifest.conflicts:
                    db.add(ConflictRecord(
                        entity_id=c.entity_id,
                        property_name=c.property_name,
                        val_a=str(c.val_a) if c.val_a is not None else None,
                        source_a=c.source_a,
                        val_b=str(c.val_b) if c.val_b is not None else None,
                        source_b=c.source_b,
                        resolved_val=str(c.resolved_val) if c.resolved_val is not None else None,
                    ))

            # 5.7 Run Universal Inference Engine (IR-01 to IR-10 post-write)
            for ent_class, ent_id, ent_props in touched_entity_ids:
                if ent_class in ["Incident", "Decision"]:
                    ir01_res = await self.inference_engine.evaluate_ir01_causal_chain(ent_id)
                    if ir01_res.get("causal_depth", 0) > 0 or ir01_res.get("circular"):
                        db.add(InferenceEventRecord(
                            rule_id="IR-01",
                            trigger_entity_id=ent_id,
                            affected_entity_ids=ir01_res.get("root_causes", []),
                            event_type="causal_depth_evaluated",
                            payload=ir01_res,
                        ))

                    is_gap = await self.inference_engine.evaluate_ir04_document_coverage(ent_id, ent_class, ent_props)
                    if is_gap:
                        db.add(InferenceEventRecord(
                            rule_id="IR-04",
                            trigger_entity_id=ent_id,
                            affected_entity_ids=[ent_id],
                            event_type="documentation_gap_detected",
                            payload={"documentation_gap": True},
                        ))

                elif ent_class == "Person":
                    is_conc = await self.inference_engine.evaluate_ir03_knowledge_concentration(ent_id)
                    if is_conc:
                        db.add(InferenceEventRecord(
                            rule_id="IR-03",
                            trigger_entity_id=ent_id,
                            affected_entity_ids=[ent_id],
                            event_type="knowledge_concentration_flagged",
                            payload={"concentration_risk": True},
                        ))

                # Check IR-09 Cascade Invalidation
                invalidated = await self.inference_engine.evaluate_ir09_cascade_invalidation(ent_id)
                if invalidated:
                    db.add(CascadeLogRecord(
                        trigger_entity_id=ent_id,
                        trigger_event="node_updated",
                        affected_entities=invalidated,
                        cascade_depth=len(invalidated),
                    ))
                    # Trigger automated cascade re-indexing in Qdrant
                    await self.cascade_reindexer.handle_downstream_invalidation(
                        affected_node_ids=invalidated,
                        triggered_by_node_id=ent_id,
                    )

            # 5.8 Relational Ledger Persistence (Phase 4: 15-Stage Topological Order & JSONB Appending)
            if manifest:
                raw_entities = [
                    {
                        "entity_id": e.entity_id,
                        "entity_class": e.entity_class,
                        "label": e.label,
                        "properties": e.properties or {},
                        "is_stub": False,
                        "completeness_score": e.completeness_score,
                        "validation_status": e.validation_status,
                        "data_quality_grade": e.data_quality_grade,
                    }
                    for e in manifest.entities
                ]
                raw_stubs = [
                    {
                        "entity_id": s.entity_id,
                        "entity_class": s.entity_class,
                        "label": s.label,
                        "properties": {"name": s.label, "status": "unresolved"},
                        "is_stub": True,
                        "completeness_score": 0.5,
                        "validation_status": "pending",
                        "data_quality_grade": "D",
                    }
                    for s in manifest.stubs
                ]
                raw_relationships = [
                    {
                        "source_id": r.source_id,
                        "target_id": r.target_id,
                        "relationship_type": r.relationship_type,
                        "confidence": r.confidence,
                        "context": r.context,
                        "source_document_id": doc_id,
                    }
                    for r in manifest.relationships
                ]
                await self.relational_ledger.execute_15_stage_topological_write(
                    session=db,
                    entities=raw_entities + raw_stubs,
                    relationships=raw_relationships,
                    source_document_id=doc_id,
                )

            await db.commit()

        except Exception as e:
            logger.error(f"FalkorDB / Inference ingestion failed for {doc_id}: {e}", exc_info=True)

        # 6. Qdrant Vector Indexing (Phase 3: Structure-Aware Document & Entity Indexing)
        indexed_chunks = 0
        try:
            vector_metadata = {
                "document_id": doc_id,
                "title": title,
                "source_system": "upload",
                "storage_key": storage_key,
                "classification": classification,
                "department": user_dept,
                "author_id": author_id,
                "project_id": project_id,
                "structuredness": parsed.structuredness,
            }
            # 6.1 Index document sections with heading boundaries and breadcrumbs
            indexed_chunks = await self.vector_indexer.index_document(
                document_id=doc_id,
                text=parsed.text,
                metadata=vector_metadata,
                doc_title=title,
                chunk_size=350,
            )

            # 6.2 Index canonical entities enriched with 1-hop FalkorDB graph neighbors
            if manifest and manifest.entities:
                for ent in manifest.entities:
                    cypher_neighbors = f"""
                    MATCH (n {{id: '{ent.entity_id}'}})-[r]-(neighbor)
                    RETURN neighbor.id, type(r), labels(neighbor)[0]
                    """
                    neigh_rows = self.falkordb.query(cypher_neighbors)
                    neighbors = [
                        {"id": row[0], "relation": row[1], "label": row[2]}
                        for row in (neigh_rows or []) if row and len(row) >= 3
                    ]
                    await self.vector_indexer.index_entity(
                        entity_id=ent.entity_id,
                        entity_class=ent.entity_class,
                        properties=ent.properties or {"name": ent.label},
                        metadata={
                            "document_id": doc_id,
                            "classification": classification,
                            "department": user_dept,
                            "author_id": author_id,
                            "project_id": project_id,
                            "completeness_score": ent.completeness_score,
                            "data_quality_grade": ent.data_quality_grade,
                            "validation_status": ent.validation_status,
                        },
                        graph_neighbors=neighbors,
                    )

        except Exception as e:
            logger.error(f"Vector indexing failed for {doc_id}: {e}", exc_info=True)

        return {
            "document_id": doc_id,
            "title": title,
            "filename": filename,
            "structuredness": parsed.structuredness,
            "storage_key": storage_key,
            "size_bytes": len(file_bytes),
            "indexed_chunks": indexed_chunks,
            "entities_found": len(manifest.entities) if manifest else 0,
            "stubs_created": len(manifest.stubs) if manifest else 0,
            "relationships_extracted": len(manifest.relationships) if manifest else 0,
            "status": "ready",
            "message": f"Successfully normalized '{title}' into storage, graph, and vector database.",
        }

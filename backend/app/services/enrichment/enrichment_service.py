from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document
from app.models.document_section import (
    DecisionMention,
    DocumentMention,
    DocumentSection,
    ExtractedEntity,
    ProjectMention,
)
from app.services.enrichment.decision_mention_extractor import DecisionMentionExtractor
from app.services.enrichment.entity_extractor import EntityExtractor
from app.services.enrichment.project_reference_extractor import ProjectReferenceExtractor
from app.services.enrichment.section_parser import SectionParser
from app.services.enrichment.sql_parser import SQLParser
from app.services.enrichment.table_parser import TableParser
from app.services.graph.document_enrichment_graph_service import DocumentEnrichmentGraphService
from app.services.storage.document_store import DocumentStore

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Orchestrates:
    1. Parsing document raw text into structured sections (headings, code, sql, table, paragraph, list).
    2. Extracting named entities (person, team, project, ticket, decision, meeting, artifact).
    3. Extracting and mapping project references & decision mentions.
    4. Parsing tables & SQL queries for section-level enrichment.
    5. Persisting structured records in PostgreSQL.
    6. Updating FalkorDB knowledge graph with REFERENCES / MENTIONS edges.
    """

    def __init__(
        self,
        section_parser: Optional[SectionParser] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        project_extractor: Optional[ProjectReferenceExtractor] = None,
        decision_extractor: Optional[DecisionMentionExtractor] = None,
        table_parser: Optional[TableParser] = None,
        sql_parser: Optional[SQLParser] = None,
        graph_service: Optional[DocumentEnrichmentGraphService] = None,
        doc_store: Optional[DocumentStore] = None,
    ):
        self.section_parser = section_parser or SectionParser()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.project_extractor = project_extractor or ProjectReferenceExtractor()
        self.decision_extractor = decision_extractor or DecisionMentionExtractor()
        self.table_parser = table_parser or TableParser()
        self.sql_parser = sql_parser or SQLParser()
        self.graph_service = graph_service or DocumentEnrichmentGraphService()
        self.doc_store = doc_store or DocumentStore()

    async def enrich_document(
        self,
        document_id: str,
        db: AsyncSession,
        raw_text: Optional[str] = None,
        force_reparse: bool = False,
    ) -> Dict[str, Any]:
        """
        Enrich a document by ID. If raw_text is not provided, fetch it via DocumentStore or Document record.
        """
        # Fetch document record
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Resolve raw text
        if not raw_text:
            if doc.storage_key:
                raw_bytes = await self.doc_store.get_document_bytes(doc.storage_key)
                if raw_bytes:
                    raw_text = raw_bytes.decode("utf-8", errors="replace")

        if not raw_text:
            raw_text = doc.title or ""

        # If re-parsing, clear old sections and extracted data
        if force_reparse:
            await db.execute(delete(DecisionMention).where(DecisionMention.document_id == document_id))
            await db.execute(delete(ProjectMention).where(ProjectMention.document_id == document_id))
            await db.execute(delete(DocumentMention).where(DocumentMention.document_id == document_id))
            await db.execute(delete(ExtractedEntity).where(ExtractedEntity.document_id == document_id))
            await db.execute(delete(DocumentSection).where(DocumentSection.document_id == document_id))
            await db.flush()

        # Check if already parsed
        existing_sections_res = await db.execute(
            select(DocumentSection).where(DocumentSection.document_id == document_id)
        )
        existing_sections = existing_sections_res.scalars().all()
        if existing_sections and not force_reparse:
            # Already parsed, return summary counts
            ent_count_res = await db.execute(
                select(ExtractedEntity).where(ExtractedEntity.document_id == document_id)
            )
            mention_count_res = await db.execute(
                select(DocumentMention).where(DocumentMention.document_id == document_id)
            )
            return {
                "document_id": document_id,
                "status": "already_enriched",
                "sections_count": len(existing_sections),
                "entities_count": len(ent_count_res.scalars().all()),
                "mentions_count": len(mention_count_res.scalars().all()),
            }

        # 1. Parse sections
        parsed_sections = self.section_parser.parse(raw_text)
        db_sections: List[DocumentSection] = []

        for ps in parsed_sections:
            db_sec = DocumentSection(
                document_id=document_id,
                section_type=ps.section_type,
                heading=ps.heading,
                content=ps.content,
                order_index=ps.order_index,
                source_start=ps.source_start,
                source_end=ps.source_end,
            )
            db.add(db_sec)
            db_sections.append(db_sec)

        await db.flush()  # assign IDs to sections

        # 2. Extract Entities & Mentions per section
        total_entities: List[ExtractedEntity] = []
        total_mentions: List[DocumentMention] = []
        seen_entity_keys = set()
        seen_mention_keys = set()

        for sec in db_sections:
            extracted = self.entity_extractor.extract(sec.content, section_id=sec.id)
            for item in extracted:
                ekey = (item.entity_type, item.normalized_value)
                if ekey not in seen_entity_keys:
                    seen_entity_keys.add(ekey)
                    ee = ExtractedEntity(
                        document_id=document_id,
                        entity_type=item.entity_type,
                        entity_value=item.entity_value,
                        normalized_value=item.normalized_value,
                        confidence_score=item.confidence_score,
                        source_section_id=sec.id,
                    )
                    db.add(ee)
                    total_entities.append(ee)

                mkey = (item.entity_type, item.normalized_value, sec.id)
                if mkey not in seen_mention_keys:
                    seen_mention_keys.add(mkey)
                    dm = DocumentMention(
                        document_id=document_id,
                        mention_type=item.entity_type,
                        mention_value=item.entity_value,
                        normalized_value=item.normalized_value,
                        source_section_id=sec.id,
                        confidence_score=item.confidence_score,
                    )
                    db.add(dm)
                    total_mentions.append(dm)

        # 3. Detect Project References
        project_refs = await self.project_extractor.extract_references(raw_text, db)
        for pref in project_refs:
            pm = ProjectMention(
                document_id=document_id,
                project_id=pref.project_id,
                mention_count=pref.mention_count,
                source_section_id=pref.source_section_id,
            )
            db.add(pm)

        # 4. Detect Decision Mentions
        decision_refs = await self.decision_extractor.extract_mentions(raw_text, db)
        for dref in decision_refs:
            dm_entry = DecisionMention(
                document_id=document_id,
                decision_id=dref.decision_id,
                mention_count=dref.mention_count,
                source_section_id=dref.source_section_id,
            )
            db.add(dm_entry)

        await db.commit()

        # 5. Enrich knowledge graph in FalkorDB
        graph_stats = await self.graph_service.sync_enrichment_to_graph(document_id, db)

        return {
            "document_id": document_id,
            "status": "completed",
            "sections_count": len(db_sections),
            "entities_count": len(total_entities),
            "mentions_count": len(total_mentions),
            "project_mentions_count": len(project_refs),
            "decision_mentions_count": len(decision_refs),
            "graph_enrichment": graph_stats,
        }


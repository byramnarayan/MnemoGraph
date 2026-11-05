from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document
from app.models.document_section import DocumentSection, ExtractedEntity
from app.services.enrichment.entity_extractor import (
    ConflictRecordData,
    EntityExtractor,
    UniversalEntity,
)
from app.services.enrichment.relationship_extractor import (
    RelationshipExtractor,
    UniversalRelationship,
)
from app.services.enrichment.section_parser import ParsedSection, SectionParser
from app.services.enrichment.sql_parser import SQLParser
from app.services.enrichment.table_parser import TableParser
from app.services.storage.document_store import DocumentStore

logger = logging.getLogger(__name__)


@dataclass
class NormalizedIngestionManifest:
    document_id: str
    structuredness: str
    sections: list[ParsedSection] = field(default_factory=list)
    entities: list[UniversalEntity] = field(default_factory=list)
    stubs: list[UniversalEntity] = field(default_factory=list)
    conflicts: list[ConflictRecordData] = field(default_factory=list)
    relationships: list[UniversalRelationship] = field(default_factory=list)


class EnrichmentService:
    """
    UKGOE Ingestion & Normalization Orchestrator (Part 1):
    1. Parses document raw text into structured sections (headings, paragraphs, code, tables, sql).
    2. Classifies entities into Universal Tiers 0-5 and executes non-linearity handlers (stubs, aliases, conflicts).
    3. Extracts Universal Relationships across the locked relationship taxonomy.
    4. Produces the NormalizedIngestionManifest ready for FalkorDB graph writes and Qdrant vector indexing.
    """

    def __init__(
        self,
        section_parser: SectionParser | None = None,
        entity_extractor: EntityExtractor | None = None,
        relationship_extractor: RelationshipExtractor | None = None,
        table_parser: TableParser | None = None,
        sql_parser: SQLParser | None = None,
        doc_store: DocumentStore | None = None,
    ):
        self.section_parser = section_parser or SectionParser()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relationship_extractor = relationship_extractor or RelationshipExtractor()
        self.table_parser = table_parser or TableParser()
        self.sql_parser = sql_parser or SQLParser()
        self.doc_store = doc_store or DocumentStore()

    async def enrich_document(
        self,
        document_id: str,
        db: AsyncSession,
        raw_text: str | None = None,
        structuredness: str = "UNSTRUCTURED",
        inferred_fields: dict[str, Any] | None = None,
        force_reparse: bool = False,
    ) -> NormalizedIngestionManifest:
        """
        Executes end-to-end normalization for a document.
        """
        # Resolve document record
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not raw_text:
            if doc and doc.storage_key:
                raw_bytes = await self.doc_store.get_document_bytes(doc.storage_key)
                if raw_bytes:
                    raw_text = raw_bytes.decode("utf-8", errors="replace")

        if not raw_text:
            raw_text = doc.title if doc else ""

        # 1. Section Parsing
        sections = self.section_parser.parse(raw_text)

        # 2. Universal Entity Extraction & Non-Linearity Handling (Tiers 0-5, Stubs, Conflicts)
        entities, stubs, conflicts = self.entity_extractor.extract_entities(
            text=raw_text,
            document_id=document_id,
            inferred_fields=inferred_fields,
        )

        # 3. Universal Relationship Extraction (Taxonomy Edges)
        all_active_entities = entities + stubs
        relationships = self.relationship_extractor.extract_relationships(
            text=raw_text,
            document_id=document_id,
            entities=all_active_entities,
        )

        # 4. Persist Document Sections in PostgreSQL
        if force_reparse:
            await db.execute(delete(ExtractedEntity).where(ExtractedEntity.document_id == document_id))
            await db.execute(delete(DocumentSection).where(DocumentSection.document_id == document_id))
            await db.flush()

        for idx, sec in enumerate(sections):
            db_sec = DocumentSection(
                document_id=document_id,
                section_type=sec.section_type,
                heading=sec.heading,
                content=sec.content,
                order_index=idx,
                source_start=sec.source_start,
                source_end=sec.source_end,
            )
            db.add(db_sec)

        # Persist extracted entity mention rows
        for ent in entities:
            db_ent = ExtractedEntity(
                document_id=document_id,
                entity_type=ent.entity_class.lower(),
                entity_value=ent.label,
                normalized_value=ent.entity_id,
                confidence_score=ent.completeness_score,
            )
            db.add(db_ent)

        await db.commit()

        return NormalizedIngestionManifest(
            document_id=document_id,
            structuredness=structuredness,
            sections=sections,
            entities=entities,
            stubs=stubs,
            conflicts=conflicts,
            relationships=relationships,
        )

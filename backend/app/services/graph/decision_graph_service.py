from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document, Person, Project, Team
from app.models.provenance import Decision, DecisionLink, ProvenanceRecord
from app.schemas.decision import DecisionCreateRequest
from app.services.graph.relation_builder import RelationBuilder
from app.services.graph.repository import GraphRepository

logger = logging.getLogger(__name__)


class DecisionGraphService:
    """Orchestrates Decision lifecycle: PostgreSQL metadata records + FalkorDB knowledge graph edges."""

    def __init__(
        self,
        graph_repo: GraphRepository | None = None,
        relation_builder: RelationBuilder | None = None,
    ):
        self.graph = graph_repo or GraphRepository()
        self.builder = relation_builder or RelationBuilder(self.graph)

    async def create_decision(self, db: AsyncSession, req: DecisionCreateRequest) -> Decision:
        # 1. Create Decision record in PostgreSQL
        decision = Decision(
            title=req.title,
            description=req.description,
            project_id=req.project_id,
            workspace_id=req.workspace_id,
            source_document_id=req.source_document_id,
            created_by_user_id=req.created_by_user_id,
            status=req.status,
        )
        db.add(decision)
        await db.commit()
        await db.refresh(decision)

        # 2. Upsert Decision node in FalkorDB
        dec_node = await self.builder.upsert_decision_node(
            decision_id=decision.id,
            title=decision.title,
            status=decision.status,
            description=decision.description,
            workspace_id=decision.workspace_id,
        )

        # 3. Create Graph Edges & Provenance Records
        # Source document link (DERIVED_FROM)
        if decision.source_document_id:
            await self.builder.link_decision_to_document(
                decision_id=decision.id,
                document_id=decision.source_document_id,
                relation="DERIVED_FROM",
            )
            db.add(
                ProvenanceRecord(
                    entity_type="Decision",
                    entity_id=decision.id,
                    source_entity_type="Document",
                    source_entity_id=decision.source_document_id,
                    relation_type="DERIVED_FROM",
                )
            )

        # Creator / Person link (CREATED_BY)
        if decision.created_by_user_id:
            await self.builder.link_decision_to_person(
                decision_id=decision.id,
                person_id_or_email=decision.created_by_user_id,
                relation="CREATED_BY",
            )
            db.add(
                ProvenanceRecord(
                    entity_type="Decision",
                    entity_id=decision.id,
                    source_entity_type="Person",
                    source_entity_id=decision.created_by_user_id,
                    relation_type="CREATED_BY",
                )
            )

        # Project link (RELATED_TO)
        if decision.project_id:
            await self.builder.link_decision_to_project(
                decision_id=decision.id,
                project_id=decision.project_id,
                relation="RELATED_TO",
            )
            db.add(
                ProvenanceRecord(
                    entity_type="Decision",
                    entity_id=decision.id,
                    source_entity_type="Project",
                    source_entity_id=decision.project_id,
                    relation_type="RELATED_TO",
                )
            )

        await db.commit()
        return decision

    async def add_decision_link(
        self,
        db: AsyncSession,
        decision_id: str,
        related_entity_type: str,
        related_entity_id: str,
        relation_type: str = "RELATED_TO",
    ) -> bool:
        # Check duplicate
        dup_res = await db.execute(
            select(DecisionLink).where(
                DecisionLink.decision_id == decision_id,
                DecisionLink.related_entity_type == related_entity_type,
                DecisionLink.related_entity_id == related_entity_id,
                DecisionLink.relation_type == relation_type,
            )
        )
        if dup_res.scalars().first():
            return True  # Already linked

        link = DecisionLink(
            decision_id=decision_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            relation_type=relation_type,
        )
        db.add(link)
        await db.commit()

        # FalkorDB edge
        dec_node = f"decision:{decision_id}"
        prefix = related_entity_type.lower()
        target_node = f"{prefix}:{related_entity_id}"
        await self.builder.link_generic(from_id=dec_node, to_id=target_node, relation=relation_type)

        return True


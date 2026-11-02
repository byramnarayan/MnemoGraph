from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provenance import Decision, DecisionLink
from app.services.graph.graph_queries import GraphQueries
from app.services.graph.repository import GraphRepository

logger = logging.getLogger(__name__)


class ProvenanceEnricher:
    """Enriches candidate retrieval hits and answering contexts with decision and provenance chains."""

    def __init__(
        self,
        graph_repo: GraphRepository | None = None,
        graph_queries: GraphQueries | None = None,
    ):
        self.graph = graph_repo or GraphRepository()
        self.queries = graph_queries or GraphQueries(self.graph)

    async def get_decisions_for_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Find all decisions derived from or connected to a document, project, person, team, or workspace."""
        results: list[dict[str, Any]] = []

        # 1. Check relational database mappings
        stmt = None
        if entity_type.lower() == "document":
            stmt = select(Decision).where(Decision.source_document_id == entity_id)
        elif entity_type.lower() == "project":
            stmt = select(Decision).where(Decision.project_id == entity_id)
        elif entity_type.lower() in ("person", "user"):
            stmt = select(Decision).where(Decision.created_by_user_id == entity_id)
        elif entity_type.lower() == "workspace":
            stmt = select(Decision).where(Decision.workspace_id == entity_id)

        if stmt is not None:
            res = await db.execute(stmt)
            for d in res.scalars().all():
                results.append({
                    "id": d.id,
                    "title": d.title,
                    "status": d.status,
                    "description": d.description,
                    "created_at": str(d.created_at),
                })

        # 2. Check DecisionLink table
        links_res = await db.execute(
            select(DecisionLink).where(
                DecisionLink.related_entity_id == entity_id,
            )
        )
        for link in links_res.scalars().all():
            if not any(r["id"] == link.decision_id for r in results):
                d_res = await db.execute(select(Decision).where(Decision.id == link.decision_id))
                dec = d_res.scalars().first()
                if dec:
                    results.append({
                        "id": dec.id,
                        "title": dec.title,
                        "status": dec.status,
                        "description": dec.description,
                        "relation": link.relation_type,
                        "created_at": str(dec.created_at),
                    })

        return results


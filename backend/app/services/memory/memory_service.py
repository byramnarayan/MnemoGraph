from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.graphiti_client import GraphitiClient
from app.services.memory.memory_recall_service import MemoryRecallService
from app.services.memory.memory_write_service import MemoryWriteService

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Unified entry point for Graphiti episodic & semantic memory overlay.
    Coordinates pre-retrieval recall, dual-store write, and session state management.
    """

    def __init__(
        self,
        graphiti_client: GraphitiClient | None = None,
        recall_service: MemoryRecallService | None = None,
        write_service: MemoryWriteService | None = None,
    ):
        self.graphiti = graphiti_client or GraphitiClient()
        self.recall = recall_service or MemoryRecallService(self.graphiti)
        self.write = write_service or MemoryWriteService(self.graphiti)

    async def pre_search_recall(
        self,
        db: AsyncSession,
        user_id: int,
        user_email: str,
        query: str,
    ) -> dict[str, Any]:
        """Recalls context before searching canonical graph + vector index."""
        return await self.recall.recall_context(
            db=db,
            user_id=user_id,
            user_email=user_email,
            current_query=query,
        )

    async def post_search_record(
        self,
        db: AsyncSession,
        user_id: int,
        user_email: str,
        session_id: str,
        query: str,
        answer: str,
        confidence_score: float,
        sources: list[dict[str, Any]],
        provenance_chain: list[dict[str, Any]],
        cypher_query: str | None,
        referenced_entity_ids: list[str] | None = None,
    ) -> str:
        """Records the synthesized episode into PostgreSQL and FalkorDB Graphiti overlay."""
        return await self.write.record_interaction(
            db=db,
            user_id=user_id,
            user_email=user_email,
            session_id=session_id,
            query=query,
            answer=answer,
            confidence_score=confidence_score,
            sources=sources,
            provenance_chain=provenance_chain,
            cypher_query=cypher_query,
            referenced_entity_ids=referenced_entity_ids,
        )


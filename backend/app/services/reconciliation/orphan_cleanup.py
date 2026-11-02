from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document
from app.models.sync_reconciliation_job import DocumentVersionState
from app.services.graph.reconciliation_graph_service import ReconciliationGraphService
from app.services.vector.stale_vector_cleanup import StaleVectorCleanup

logger = logging.getLogger(__name__)


class OrphanCleanup:
    """
    Cleans orphan documents, removes dangling graph nodes/edges, and purges
    associated vector points from Qdrant.
    """

    def __init__(
        self,
        graph_service: Optional[ReconciliationGraphService] = None,
        vector_cleanup: Optional[StaleVectorCleanup] = None,
    ):
        self.graph_service = graph_service or ReconciliationGraphService()
        self.vector_cleanup = vector_cleanup or StaleVectorCleanup()

    async def mark_deleted_and_purge(
        self,
        document_id: str,
        db: AsyncSession,
    ) -> dict[str, int]:
        """
        Marks document as deleted in version state, removes graph node/edges,
        and deletes vector chunks from Qdrant.
        """
        # Mark state
        stmt = select(DocumentVersionState).where(DocumentVersionState.document_id == document_id)
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        if state:
            state.is_deleted = True
            await db.flush()

        # Remove graph edges
        edges_removed = await self.graph_service.remove_document_edges(document_id)
        # Delete graph node
        await self.graph_service.delete_document_node(document_id)

        # Delete vectors
        vectors_removed = await self.vector_cleanup.delete_document_vectors(document_id)

        logger.info(
            f"Purged document {document_id}: edges={edges_removed}, vectors={vectors_removed}"
        )
        return {
            "edges_removed": edges_removed,
            "vectors_removed": vectors_removed,
        }


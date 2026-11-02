from __future__ import annotations

import logging
from typing import Optional
from app.services.graph.reconciliation_graph_service import ReconciliationGraphService

logger = logging.getLogger(__name__)


class StaleEdgeCleaner:
    """
    Cleans stale graph edges associated with modified or deleted documents.
    """

    def __init__(self, graph_service: Optional[ReconciliationGraphService] = None):
        self.graph_service = graph_service or ReconciliationGraphService()

    async def clean_edges_for_document(self, document_id: str) -> int:
        """Removes stale edges for a document."""
        return await self.graph_service.remove_document_edges(document_id)


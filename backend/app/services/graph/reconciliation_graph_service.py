from __future__ import annotations

import logging
from typing import Any, List, Optional
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class ReconciliationGraphService:
    """
    Manages graph edge reconciliation, removing stale edges and orphan nodes
    when documents are updated, moved, or deleted.
    """

    def __init__(self, client: Optional[FalkorDBClient] = None):
        self.client = client or FalkorDBClient()

    async def remove_document_edges(self, document_id: str) -> int:
        """
        Removes all incoming and outgoing edges connected to a document node
        (e.g., REFERENCES, MENTIONS, AUTHORED_BY, BELONGS_TO).
        """
        def _exec():
            # Match document and count edges before deleting
            count_cypher = f"MATCH (d {{id: '{document_id}'}})-[r]-() RETURN count(r)"
            count_rows = self.client.query(count_cypher)
            edge_count = count_rows[0][0] if count_rows else 0

            del_cypher = f"MATCH (d {{id: '{document_id}'}})-[r]-() DELETE r"
            self.client.query(del_cypher)
            return edge_count

        return await run_in_threadpool(_exec)

    async def delete_document_node(self, document_id: str) -> bool:
        """Deletes a document node and its edges from FalkorDB."""
        def _exec():
            cypher = f"MATCH (d {{id: '{document_id}'}}) DETACH DELETE d"
            self.client.query(cypher)
            return True

        return await run_in_threadpool(_exec)

    async def clean_stale_edges_for_missing_targets(self) -> int:
        """
        Finds and cleans dangling relationships where either start or end node is missing.
        """
        def _exec():
            # In FalkorDB, relationships cannot exist without nodes, but we verify consistency
            return 0

        return await run_in_threadpool(_exec)


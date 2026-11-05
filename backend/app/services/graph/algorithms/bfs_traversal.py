from __future__ import annotations

import logging
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.permissions.permission_resolver import PermissionResolver
from app.services.graph.algorithms.types import GraphPath

logger = logging.getLogger(__name__)


class BFSTraversalEngine:
    """
    Executes bounded FalkorDB algo.BFS queries with zero-leakage ABAC pruning (INV-05).
    """

    def __init__(
        self,
        falkor: FalkorDBClient | None = None,
        perm_resolver: PermissionResolver | None = None,
    ):
        self.falkor = falkor or FalkorDBClient()
        self.security = perm_resolver or PermissionResolver()

    async def traverse_bfs(
        self,
        anchor_id: str,
        rel_type: str = "CONNECTED_TO",
        max_depth: int = 2,
        user_clearance: str = "Internal",
    ) -> list[GraphPath]:
        clean_id = anchor_id.replace("'", "\\'")
        bounded_depth = min(max(1, max_depth), 3)

        def _run_query():
            cypher = f"""
            MATCH (src {{id: '{clean_id}'}})
            CALL algo.BFS(src, {bounded_depth}, '{rel_type}') YIELD nodes, edges
            RETURN [n IN nodes | {{id: n.id, classification: n.classification, name: coalesce(n.name, n.title, n.id)}}],
                   [e IN edges | type(e)]
            LIMIT 25
            """
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run_query)
        except Exception as exc:
            logger.warning(f"algo.BFS execution fallback for {anchor_id}: {exc}")
            return []

        paths: list[GraphPath] = []
        for r in rows:
            if not r or len(r) < 2:
                continue
            nodes_data = r[0] or []
            edges_data = r[1] or []

            # INV-05 Security Boundary Check
            authorized = True
            node_ids: list[str] = [anchor_id]
            for n in nodes_data:
                classification = n.get("classification") or "Internal"
                if not self.security.is_node_authorized(classification, user_clearance):
                    authorized = False
                    break
                node_ids.append(n.get("name") or n.get("id"))

            if authorized and len(node_ids) > 1:
                paths.append(
                    GraphPath(
                        source_id=anchor_id,
                        target_id=node_ids[-1],
                        nodes=node_ids,
                        relationships=edges_data,
                        length=len(edges_data),
                    )
                )

        return paths


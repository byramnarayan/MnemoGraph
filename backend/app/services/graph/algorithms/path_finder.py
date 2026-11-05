from __future__ import annotations

import logging
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.permissions.permission_resolver import PermissionResolver
from app.services.graph.algorithms.types import GraphPath

logger = logging.getLogger(__name__)


class PathFinderEngine:
    """
    Executes bounded FalkorDB algo.SPpaths and algo.SSpaths with ABAC pruning (INV-05).
    """

    def __init__(
        self,
        falkor: FalkorDBClient | None = None,
        perm_resolver: PermissionResolver | None = None,
    ):
        self.falkor = falkor or FalkorDBClient()
        self.security = perm_resolver or PermissionResolver()

    async def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_len: int = 4,
        user_clearance: str = "Internal",
    ) -> list[GraphPath]:
        clean_src = source_id.replace("'", "\\'")
        clean_tgt = target_id.replace("'", "\\'")
        bounded_len = min(max(1, max_len), 5)

        def _run_query():
            cypher = f"""
            MATCH (a {{id: '{clean_src}'}}), (b {{id: '{clean_tgt}'}})
            CALL algo.SPpaths({{sourceNode: a, targetNode: b, maxLen: {bounded_len}}}) YIELD path
            RETURN [n IN nodes(path) | {{id: n.id, classification: n.classification, name: coalesce(n.name, n.title, n.id)}}],
                   [r IN relationships(path) | type(r)],
                   length(path)
            LIMIT 10
            """
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run_query)
        except Exception as exc:
            logger.warning(f"algo.SPpaths fallback: {exc}")
            return []

        paths: list[GraphPath] = []
        for r in rows:
            if not r or len(r) < 3:
                continue
            nodes_data = r[0] or []
            rels_data = r[1] or []
            p_len = r[2] or 0

            # INV-05 Clearance Check
            authorized = True
            node_names: list[str] = []
            for n in nodes_data:
                classification = n.get("classification") or "Internal"
                if not self.security.is_node_authorized(classification, user_clearance):
                    authorized = False
                    break
                node_names.append(n.get("name") or n.get("id"))

            if authorized and node_names:
                paths.append(
                    GraphPath(
                        source_id=source_id,
                        target_id=target_id,
                        nodes=node_names,
                        relationships=rels_data,
                        length=p_len,
                    )
                )

        return paths

    async def find_source_to_many(
        self,
        source_id: str,
        max_len: int = 3,
        user_clearance: str = "Internal",
    ) -> list[GraphPath]:
        clean_src = source_id.replace("'", "\\'")
        bounded_len = min(max(1, max_len), 4)

        def _run_query():
            cypher = f"""
            MATCH (a {{id: '{clean_src}'}})
            CALL algo.SSpaths({{sourceNode: a, maxLen: {bounded_len}}}) YIELD path
            RETURN [n IN nodes(path) | {{id: n.id, classification: n.classification, name: coalesce(n.name, n.title, n.id)}}],
                   [r IN relationships(path) | type(r)],
                   length(path)
            LIMIT 15
            """
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run_query)
        except Exception as exc:
            logger.warning(f"algo.SSpaths fallback: {exc}")
            return []

        paths: list[GraphPath] = []
        for r in rows:
            if not r or len(r) < 3:
                continue
            nodes_data = r[0] or []
            rels_data = r[1] or []
            p_len = r[2] or 0

            authorized = True
            node_names: list[str] = []
            for n in nodes_data:
                classification = n.get("classification") or "Internal"
                if not self.security.is_node_authorized(classification, user_clearance):
                    authorized = False
                    break
                node_names.append(n.get("name") or n.get("id"))

            if authorized and len(node_names) > 1:
                paths.append(
                    GraphPath(
                        source_id=source_id,
                        target_id=node_names[-1],
                        nodes=node_names,
                        relationships=rels_data,
                        length=p_len,
                    )
                )

        return paths


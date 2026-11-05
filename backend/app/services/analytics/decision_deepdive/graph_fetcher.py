from __future__ import annotations

import logging
from typing import Any
from starlette.concurrency import run_in_threadpool
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.indexer import VectorIndexer

logger = logging.getLogger(__name__)


class DeepDiveDataFetcher:
    """
    Fetches multi-hop FalkorDB graph relationships and Qdrant semantic precedents.
    """

    def __init__(self, falkor: FalkorDBClient, vector_indexer: VectorIndexer):
        self.falkor = falkor
        self.indexer = vector_indexer

    async def fetch_graph_neighborhood(self, decision_id: str) -> dict[str, Any]:
        clean_id = decision_id.replace("'", "\\'")

        def _query():
            cypher = f"""
            MATCH (d:Decision {{id: '{clean_id}'}})
            OPTIONAL MATCH (p:Person)-[:DECIDED|MADE_BY]->(d)
            OPTIONAL MATCH (t:Task)-[:RAISED_FROM]->(d)
            OPTIONAL MATCH (t)-[:ASSIGNED_TO]->(assignee:Person)
            OPTIONAL MATCH (d)-[:AFFECTS]->(s)
            OPTIONAL MATCH (s)-[:CONNECTED_TO|DEPENDS_ON]-(neighbor)
            RETURN d, p, t, assignee, s, neighbor
            LIMIT 25
            """
            return self.falkor.query(cypher)

        rows = await run_in_threadpool(_query)

        decision_data: dict[str, Any] = {}
        person_name = "Institutional Architect"
        tasks: list[dict[str, Any]] = []
        systems: list[str] = []
        neighbors: list[str] = []

        for r in rows:
            if not decision_data and len(r) > 0 and r[0]:
                decision_data = getattr(r[0], "properties", {})
            if len(r) > 1 and r[1]:
                p_props = getattr(r[1], "properties", {})
                person_name = p_props.get("name") or p_props.get("full_name") or person_name
            if len(r) > 2 and r[2]:
                t_props = getattr(r[2], "properties", {})
                if t_props.get("title") and t_props not in tasks:
                    tasks.append(t_props)
            if len(r) > 4 and r[4]:
                s_props = getattr(r[4], "properties", {})
                s_name = s_props.get("name") or s_props.get("title") or s_props.get("id")
                if s_name and s_name not in systems:
                    systems.append(s_name)
            if len(r) > 5 and r[5]:
                n_props = getattr(r[5], "properties", {})
                n_name = n_props.get("name") or n_props.get("title") or n_props.get("id")
                if n_name and n_name not in neighbors:
                    neighbors.append(n_name)

        return {
            "decision": decision_data,
            "decision_maker": person_name,
            "tasks": tasks,
            "systems": systems,
            "neighbors": neighbors,
        }

    async def fetch_semantic_precedents(self, scope: str, limit: int = 3) -> list[str]:
        query = f"Incident post-mortem root cause and lesson learned on {scope}"
        hits = await self.indexer.search(query=query, limit=limit)
        return [
            h.get("payload", {}).get("text", "")[:350]
            for h in hits
            if h.get("payload") and h.get("payload", {}).get("text")
        ]


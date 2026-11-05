from __future__ import annotations

import logging
from typing import Any

from starlette.concurrency import run_in_threadpool
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


class TimelineGraphExtractor:
    """
    Extracts multi-hop operational chains connecting People, Decisions, Tasks,
    Operational Changes, Affected Systems/Sites, and Incidents from FalkorDB.
    """

    def __init__(self, falkor_client: FalkorDBClient | None = None):
        self.client = falkor_client or FalkorDBClient()

    async def extract_chains_for_scope(
        self,
        entity_id: str | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        """
        Executes parameterized openCypher query to pull institutional chains.
        """
        def _query():
            if entity_id:
                clean_id = entity_id.replace("'", "\\'")
                cypher = f"""
                MATCH (d:Decision)
                WHERE d.id = '{clean_id}' OR d.affected_systems CONTAINS '{clean_id}' OR d.project_id = '{clean_id}'
                OPTIONAL MATCH (p:Person)-[r_made:MADE_BY|DECIDED]->(d)
                OPTIONAL MATCH (t:Task)-[r_task:RAISED_FROM|RAISED_FROM_DECISION]->(d)
                OPTIONAL MATCH (t)-[r_assign:ASSIGNED_TO]->(assignee:Person)
                OPTIONAL MATCH (d)-[r_aff:AFFECTS|APPLIES_TO]->(s)
                OPTIONAL MATCH (i:Incident)-[r_inc:AFFECTS|CAUSED_BY*1..2]-(s)
                RETURN d, p, t, assignee, s, i
                LIMIT {limit}
                """
            else:
                cypher = f"""
                MATCH (d:Decision)
                OPTIONAL MATCH (p:Person)-[r_made:MADE_BY|DECIDED]->(d)
                OPTIONAL MATCH (t:Task)-[r_task:RAISED_FROM|RAISED_FROM_DECISION]->(d)
                OPTIONAL MATCH (t)-[r_assign:ASSIGNED_TO]->(assignee:Person)
                OPTIONAL MATCH (d)-[r_aff:AFFECTS|APPLIES_TO]->(s)
                OPTIONAL MATCH (i:Incident)-[r_inc:AFFECTS|CAUSED_BY*1..2]-(s)
                RETURN d, p, t, assignee, s, i
                LIMIT {limit}
                """
            return self.client.query(cypher)

        try:
            rows = await run_in_threadpool(_query)
            extracted = []
            for row in rows:
                extracted.append({
                    "decision": getattr(row[0], "properties", {}) if len(row) > 0 and row[0] else {},
                    "person": getattr(row[1], "properties", {}) if len(row) > 1 and row[1] else {},
                    "task": getattr(row[2], "properties", {}) if len(row) > 2 and row[2] else {},
                    "assignee": getattr(row[3], "properties", {}) if len(row) > 3 and row[3] else {},
                    "system": getattr(row[4], "properties", {}) if len(row) > 4 and row[4] else {},
                    "incident": getattr(row[5], "properties", {}) if len(row) > 5 and row[5] else {},
                })
            return extracted
        except Exception as e:
            logger.warning(f"[TimelineGraphExtractor] Traversal error: {e}")
            return []


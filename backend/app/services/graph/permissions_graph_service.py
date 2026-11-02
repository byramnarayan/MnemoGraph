from __future__ import annotations

import logging
from typing import List, Optional
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.schema import RelationType

logger = logging.getLogger(__name__)


class PermissionsGraphService:
    """
    Reflects HAS_PERMISSION and OWNS relationships in FalkorDB.
    """

    def __init__(self, client: Optional[FalkorDBClient] = None):
        self.client = client or FalkorDBClient()

    async def link_permission(
        self,
        principal_id: str,
        entity_id: str,
        access_level: str = "READ",
    ) -> None:
        def _exec():
            cypher = f"""
            MATCH (p {{id: '{principal_id}'}}), (e {{id: '{entity_id}'}})
            MERGE (p)-[r:{RelationType.HAS_PERMISSION.value}]->(e)
            SET r.access_level = '{access_level}'
            RETURN type(r)
            """
            self.client.query(cypher)

        await run_in_threadpool(_exec)


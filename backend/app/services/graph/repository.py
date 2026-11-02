from __future__ import annotations

import logging
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class GraphRepository:
    """Repository pattern for graph persistence, queries, and neighborhood traversal in FalkorDB."""

    def __init__(self, client: FalkorDBClient | None = None):
        self.client = client or FalkorDBClient()

    def _format_props(self, props: dict[str, Any]) -> str:
        items = []
        for k, v in props.items():
            if isinstance(v, str):
                escaped = v.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                items.append(f"{k}: '{escaped}'")
            elif isinstance(v, bool):
                items.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                items.append(f"{k}: {v}")
            elif isinstance(v, list):
                safe_list = ", ".join([f"'{str(x).replace("'", "\\'")}'" for x in v])
                items.append(f"{k}: [{safe_list}]")
        return ", ".join(items)

    async def upsert_node(
        self,
        label: str | NodeLabel,
        entity_id: str,
        properties: dict[str, Any],
    ) -> None:
        """Upsert a node by deterministic entity_id."""
        def _exec():
            lbl = label.value if isinstance(label, NodeLabel) else label
            props = dict(properties)
            props["id"] = entity_id
            prop_str = self._format_props(props)
            cypher = f"MERGE (n:{lbl} {{id: '{entity_id}'}}) SET n += {{{prop_str}}} RETURN n.id"
            self.client.query(cypher)

        await run_in_threadpool(_exec)

    async def upsert_edge(
        self,
        from_id: str,
        to_id: str,
        relation: str | RelationType,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a directed relationship between two nodes by id."""
        def _exec():
            rel = relation.value if isinstance(relation, RelationType) else relation
            props = properties or {}
            prop_str = self._format_props(props)
            set_clause = f"SET r += {{{prop_str}}}" if prop_str else ""
            cypher = f"""
            MATCH (a {{id: '{from_id}'}}), (b {{id: '{to_id}'}})
            MERGE (a)-[r:{rel}]->(b)
            {set_clause}
            RETURN type(r)
            """
            self.client.query(cypher)

        await run_in_threadpool(_exec)

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch node properties and primary label."""
        def _exec():
            cypher = f"MATCH (n {{id: '{entity_id}'}}) RETURN labels(n), properties(n)"
            rows = self.client.query(cypher)
            if rows:
                labels, props = rows[0]
                return {
                    "id": entity_id,
                    "label": labels[0] if labels else "Unknown",
                    "properties": props or {},
                }
            return None

        return await run_in_threadpool(_exec)

    async def get_related_entities(self, entity_id: str) -> dict[str, Any]:
        """Fetch incoming and outgoing neighborhood for an entity."""
        def _exec():
            out_cypher = f"""
            MATCH (a {{id: '{entity_id}'}})-[r]->(b)
            RETURN type(r), b.id, labels(b), properties(r)
            """
            in_cypher = f"""
            MATCH (a)-[r]->(b {{id: '{entity_id}'}})
            RETURN type(r), a.id, labels(a), properties(r)
            """
            out_rows = self.client.query(out_cypher)
            in_rows = self.client.query(in_cypher)

            outgoing = [
                {
                    "relation": row[0],
                    "target_id": row[1],
                    "target_label": row[2][0] if row[2] else "Entity",
                    "properties": row[3] or {},
                }
                for row in out_rows
            ]

            incoming = [
                {
                    "relation": row[0],
                    "target_id": row[1],
                    "target_label": row[2][0] if row[2] else "Entity",
                    "properties": row[3] or {},
                }
                for row in in_rows
            ]

            base = self.client.query(f"MATCH (n {{id: '{entity_id}'}}) RETURN labels(n), properties(n)")
            props = base[0][1] if base else {}
            lbl = base[0][0][0] if base and base[0][0] else "Entity"

            return {
                "entity_id": entity_id,
                "label": lbl,
                "properties": props or {},
                "incoming": incoming,
                "outgoing": outgoing,
            }

        return await run_in_threadpool(_exec)

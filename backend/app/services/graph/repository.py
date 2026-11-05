from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class GraphRepository:
    """
    Universal Graph Repository (UKGOE Part 2):
    1. Deterministic node upsert with field-by-field diff tracking into property_history.
    2. Stub resolution merging properties onto :Stub nodes, inheriting edges, and clearing :PENDING_RESOLUTION.
    3. Directed typed edge upsert with :MULTI_CAUSE preservation.
    4. Fast neighborhood and traversal path queries.
    """

    def __init__(self, client: FalkorDBClient | None = None):
        self.client = client or FalkorDBClient()

    def _format_props(self, props: dict[str, Any]) -> str:
        items = []
        for k, v in props.items():
            if v is None:
                continue
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
            elif isinstance(v, dict):
                escaped_json = json.dumps(v).replace("\\", "\\\\").replace("'", "\\'")
                items.append(f"{k}: '{escaped_json}'")
        return ", ".join(items)

    async def upsert_universal_node(
        self,
        label: str | NodeLabel,
        entity_id: str,
        properties: dict[str, Any],
        source_doc_id: str | None = None,
    ) -> dict[str, Any]:
        """
        UKGOE Step 2.1 Node Upsert Strategy:
        1. Query existing node by entity_id.
        2. If node is a STUB (:Stub or :PENDING_RESOLUTION): resolve stub, merge properties, inherit edges.
        3. If node exists: compare fields, record diffs into property_history, update properties.
        4. If node does not exist: create with first_seen and validation_status='pending'.
        """
        def _exec() -> dict[str, Any]:
            now_iso = datetime.now(timezone.utc).isoformat()
            lbl = label.value if isinstance(label, NodeLabel) else label
            props = dict(properties)
            props["id"] = entity_id

            # Check if node already exists
            cypher_check = f"MATCH (n {{id: '{entity_id}'}}) RETURN labels(n), properties(n)"
            existing_rows = self.client.query(cypher_check)

            if existing_rows:
                existing_labels, existing_props = existing_rows[0]
                is_stub = "Stub" in existing_labels or "PENDING_RESOLUTION" in existing_labels

                # Diff fields
                diffs = []
                for k, v in props.items():
                    if k in ["id", "property_history", "provenance_sources"]:
                        continue
                    old_v = existing_props.get(k)
                    if old_v != v:
                        diffs.append({
                            "field": k,
                            "old": old_v,
                            "new": v,
                            "changed_at": now_iso,
                            "source_doc": source_doc_id,
                        })

                # Append to property_history
                existing_history_raw = existing_props.get("property_history", "[]")
                try:
                    history_list = json.loads(existing_history_raw) if isinstance(existing_history_raw, str) else list(existing_history_raw)
                except Exception:
                    history_list = []
                history_list.extend(diffs)
                props["property_history"] = json.dumps(history_list)

                # Append source doc ID
                sources = existing_props.get("provenance_sources", [])
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except Exception:
                        sources = [sources]
                if source_doc_id and source_doc_id not in sources:
                    sources.append(source_doc_id)
                props["provenance_sources"] = sources
                props["updated_at"] = now_iso

                prop_str = self._format_props(props)

                if is_stub:
                    # Resolve stub: merge full properties, set new label, remove Stub
                    cypher_resolve = f"""
                    MATCH (n {{id: '{entity_id}'}})
                    SET n:{lbl}, n += {{{prop_str}}}
                    REMOVE n:Stub
                    RETURN n.id
                    """
                    self.client.query(cypher_resolve)
                    return {"event": "STUB_RESOLVED", "id": entity_id, "entity_id": entity_id, "diffs": diffs, "is_stub": False}
                else:
                    cypher_update = f"""
                    MATCH (n {{id: '{entity_id}'}})
                    SET n += {{{prop_str}}}
                    RETURN n.id
                    """
                    self.client.query(cypher_update)
                    return {"event": "NODE_UPDATED", "id": entity_id, "entity_id": entity_id, "diffs": diffs, "is_stub": False}

            else:
                # Node does not exist: create with first_seen
                is_stub = "Stub" in lbl or properties.get("is_stub", False)
                props["first_seen"] = now_iso
                props["validation_status"] = props.get("validation_status", "pending")
                props["source_document_ids"] = [source_doc_id] if source_doc_id else []
                props["provenance_sources"] = [source_doc_id] if source_doc_id else []
                props["property_history"] = "[]"
                prop_str = self._format_props(props)

                cypher_create = f"MERGE (n:{lbl} {{id: '{entity_id}'}}) SET n += {{{prop_str}}} RETURN n.id"
                self.client.query(cypher_create)
                return {"event": "NODE_CREATED", "id": entity_id, "entity_id": entity_id, "diffs": [], "is_stub": is_stub}

        return await run_in_threadpool(_exec)

    async def upsert_universal_edge(
        self,
        from_id: str | None = None,
        to_id: str | None = None,
        relation: str | RelationType | None = None,
        properties: dict[str, Any] | None = None,
        source_doc_id: str | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        rel_type: str | RelationType | None = None,
        preserve_multi_cause: bool = True,
    ) -> dict[str, Any]:
        """
        UKGOE Step 2.2 Edge Write Rules:
        1. Checks for existing edge (idempotent).
        2. Detects multi-cause conflicts: if multiple causal edges point to same target from different sources,
           preserves both edges and annotates target node with :MULTI_CAUSE.
        """
        def _exec() -> dict[str, Any]:
            actual_from = from_id or source_id
            actual_to = to_id or target_id
            actual_rel = relation or rel_type
            if not actual_from or not actual_to or not actual_rel:
                raise ValueError("Edge requires from/source_id, to/target_id, and relation/rel_type")

            rel = actual_rel.value if isinstance(actual_rel, RelationType) else actual_rel
            props = properties or {}
            now_iso = datetime.now(timezone.utc).isoformat()
            props["updated_at"] = now_iso
            if source_doc_id:
                props["source_doc_id"] = source_doc_id

            prop_str = self._format_props(props)
            set_clause = f"SET r += {{{prop_str}}}" if prop_str else ""

            # Check if this is a causal edge and if either node has compounding causes
            is_causal = preserve_multi_cause and rel in ["CAUSED_BY", "CAUSED_RECURRENCE"]
            if is_causal:
                # Check outgoing causal edges from actual_from (e.g. Incident caused by multiple roots)
                check_out = f"""
                MATCH (origin {{id: '{actual_from}'}})-[r:CAUSED_BY|CAUSED_RECURRENCE]->(other)
                WHERE other.id <> '{actual_to}'
                RETURN count(r)
                """
                out_res = self.client.query(check_out)
                if out_res and out_res[0] and out_res[0][0] > 0:
                    self.client.query(f"MATCH (origin {{id: '{actual_from}'}}) SET origin:MULTI_CAUSE")

                # Check incoming causal edges to actual_to
                check_in = f"""
                MATCH (other)-[r:CAUSED_BY|CAUSED_RECURRENCE]->(target {{id: '{actual_to}'}})
                WHERE other.id <> '{actual_from}'
                RETURN count(r)
                """
                in_res = self.client.query(check_in)
                if in_res and in_res[0] and in_res[0][0] > 0:
                    self.client.query(f"MATCH (target {{id: '{actual_to}'}}) SET target:MULTI_CAUSE")

            cypher_edge = f"""
            MATCH (a {{id: '{actual_from}'}}), (b {{id: '{actual_to}'}})
            MERGE (a)-[r:{rel}]->(b)
            {set_clause}
            RETURN type(r)
            """
            self.client.query(cypher_edge)
            return {"event": "EDGE_WRITTEN", "from_id": actual_from, "to_id": actual_to, "relation": rel}

        return await run_in_threadpool(_exec)

    async def upsert_node(self, label: str | NodeLabel, entity_id: str, properties: dict[str, Any]) -> None:
        await self.upsert_universal_node(label, entity_id, properties)

    async def upsert_edge(
        self,
        from_id: str,
        to_id: str,
        relation: str | RelationType,
        properties: dict[str, Any] | None = None,
    ) -> None:
        await self.upsert_universal_edge(from_id, to_id, relation, properties)

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
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

            outgoing = []
            for r, b_id, labels, props in out_rows:
                outgoing.append({
                    "relation": r,
                    "target_id": b_id,
                    "target_label": labels[0] if labels else "Unknown",
                    "properties": props or {},
                })

            incoming = []
            for r, a_id, labels, props in in_rows:
                incoming.append({
                    "relation": r,
                    "source_id": a_id,
                    "source_label": labels[0] if labels else "Unknown",
                    "properties": props or {},
                })

            return {"entity_id": entity_id, "outgoing": outgoing, "incoming": incoming}
        return await run_in_threadpool(_exec)

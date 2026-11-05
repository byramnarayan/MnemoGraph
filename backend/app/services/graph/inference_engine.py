from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.embeddings import embed_texts

logger = logging.getLogger(__name__)


class UniversalInferenceEngine:
    """
    Universal Inference Engine (UKGOE Step 2.3):
    Executes rules IR-01 through IR-10 automatically post-write.
    """

    def __init__(self, falkordb_client: FalkorDBClient | None = None):
        self.client = falkordb_client or FalkorDBClient()

    # -------------------------------------------------------------
    # IR-01: Causal Chain Propagation
    # -------------------------------------------------------------
    async def evaluate_ir01_causal_chain(self, target_entity_id: str) -> dict[str, Any]:
        """
        Walks causal chain upstream to depth 5.
        Annotates target with causal_chain_depth and root_cause_ids.
        Detects circular causation loops.
        """
        def _exec():
            cypher = f"""
            MATCH path = (target {{id: '{target_entity_id}'}})-[:CAUSED_BY|CAUSED_RECURRENCE*1..5]->(root)
            WHERE NOT (root)-[:CAUSED_BY|CAUSED_RECURRENCE]->()
            RETURN length(path) AS depth, root.id AS root_id
            """
            rows = self.client.query(cypher)
            max_depth = 0
            root_ids = set()

            for depth, root_id in rows:
                if depth > max_depth:
                    max_depth = depth
                if root_id:
                    root_ids.add(root_id)

            # Cycle detection
            cycle_check = f"""
            MATCH path = (target {{id: '{target_entity_id}'}})-[:CAUSED_BY|CAUSED_RECURRENCE*1..5]->(target)
            RETURN count(path)
            """
            cycle_res = self.client.query(cycle_check)
            is_circular = cycle_res[0][0] > 0 if cycle_res and cycle_res[0] else False

            root_list_str = ", ".join([f"'{rid}'" for rid in root_ids])
            update_cypher = f"""
            MATCH (target {{id: '{target_entity_id}'}})
            SET target.causal_chain_depth = {max_depth},
                target.root_cause_ids = [{root_list_str}],
                target.circular_causation = {'true' if is_circular else 'false'}
            RETURN target.id
            """
            self.client.query(update_cypher)
            return {"rule_id": "IR-01", "entity_id": target_entity_id, "causal_depth": max_depth, "root_causes": list(root_ids), "circular": is_circular}

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-02: Blocking Dependency Propagation
    # -------------------------------------------------------------
    async def evaluate_ir02_blocking_dependency(self, dependency_entity_id: str, new_status: str) -> list[str]:
        """
        If dependency is in [cancelled, failed, on_hold, overdue],
        mark all downstream dependents with risk_flag = 'blocked_dependency'.
        """
        def _exec():
            is_blocking = new_status.lower() in ["cancelled", "failed", "on_hold", "overdue", "delayed"]
            if not is_blocking:
                return []

            cypher = f"""
            MATCH (dependent)-[:DEPENDS_ON]->(dep {{id: '{dependency_entity_id}'}})
            SET dependent.risk_flag = 'blocked_dependency',
                dependent.blocked_by = '{dependency_entity_id}'
            RETURN dependent.id
            """
            rows = self.client.query(cypher)
            return [row[0] for row in rows if row and row[0]]

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-03: Knowledge Concentration Detection
    # -------------------------------------------------------------
    async def evaluate_ir03_knowledge_concentration(self, person_id: str, threshold: int = 5) -> bool:
        """
        Count critical open/overdue tasks or incidents assigned to person.
        If count > threshold, flag concentration_risk = true.
        """
        def _exec():
            cypher = f"""
            MATCH (item)-[:ASSIGNED_TO|LEADS]->(p:Person {{id: '{person_id}'}})
            WHERE item.status IN ['open', 'in_progress', 'overdue']
              AND (item.severity IN ['P1', 'P2', 'critical', 'high'] OR item.priority IN ['critical', 'high'])
            RETURN count(item)
            """
            rows = self.client.query(cypher)
            cnt = rows[0][0] if rows and rows[0] else 0
            is_risk = cnt > threshold

            tag_cypher = f"""
            MATCH (p:Person {{id: '{person_id}'}})
            SET p.concentration_risk = {'true' if is_risk else 'false'},
                p.owned_critical_items = {cnt}
            RETURN p.id
            """
            self.client.query(tag_cypher)
            return is_risk

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-04: Document Coverage Enforcement
    # -------------------------------------------------------------
    async def evaluate_ir04_document_coverage(self, entity_id: str, entity_class: str, properties: dict[str, Any]) -> bool:
        """
        P1/P2/critical incident or negative decision must have a Document linking to it.
        If not found, set documentation_gap = true.
        """
        def _exec():
            severity = str(properties.get("severity", "")).lower()
            outcome = str(properties.get("outcome", "")).lower()

            needs_doc = (entity_class == "Incident" and severity in ["p1", "p2", "critical"]) or (entity_class == "Decision" and outcome == "negative")
            if not needs_doc:
                return False

            check_doc = f"""
            MATCH (d:Document)-[:DOCUMENTS]->(target {{id: '{entity_id}'}})
            RETURN count(d)
            """
            rows = self.client.query(check_doc)
            has_doc = rows[0][0] > 0 if rows and rows[0] else False
            is_gap = not has_doc

            update_cypher = f"""
            MATCH (target {{id: '{entity_id}'}})
            SET target.documentation_gap = {'true' if is_gap else 'false'}
            """
            self.client.query(update_cypher)
            return is_gap

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-05: Temporal Coherence Check
    # -------------------------------------------------------------
    def evaluate_ir05_temporal_coherence(self, properties: dict[str, Any]) -> tuple[bool, str]:
        """
        Validates start < resolution datetime.
        Returns (is_valid, validation_status)
        """
        start = properties.get("start_datetime") or properties.get("start_date")
        end = properties.get("resolution_datetime") or properties.get("actual_end_date")
        if start and end and str(end) < str(start):
            return False, "temporal_conflict"
        return True, "valid"

    # -------------------------------------------------------------
    # IR-06: Effectiveness Cascade
    # -------------------------------------------------------------
    async def evaluate_ir06_effectiveness_cascade(
        self,
        action_id: str,
        effectiveness_label: str,
        recurrence_ref: str | None,
        source_incident_id: str | None,
    ) -> dict[str, Any]:
        """
        When action is ineffective:
        1. Create CAUSED_RECURRENCE edge to recurrence incident.
        2. Set recurrence_risk = true on source incident.
        3. Flag sibling actions with recurrence_risk_inherited = true.
        """
        def _exec():
            if effectiveness_label.lower() != "ineffective" or not recurrence_ref or not source_incident_id:
                return {}

            # Create recurrence edge
            cypher_edge = f"""
            MATCH (src:Incident {{id: '{source_incident_id}'}}), (rec:Incident {{id: '{recurrence_ref}'}})
            MERGE (src)-[r:CAUSED_RECURRENCE]->(rec)
            SET src.recurrence_risk = true,
                src.recurrence_count = coalesce(src.recurrence_count, 0) + 1
            """
            self.client.query(cypher_edge)

            # Flag sibling actions
            cypher_siblings = f"""
            MATCH (sibling:Task)-[:RESOLVED_BY|PREVENTED_BY]-(src:Incident {{id: '{source_incident_id}'}})
            WHERE sibling.id <> '{action_id}' AND sibling.status IN ['open', 'in_progress']
            SET sibling.recurrence_risk_inherited = true
            RETURN sibling.id
            """
            sibling_rows = self.client.query(cypher_siblings)
            siblings = [r[0] for r in sibling_rows if r and r[0]]
            return {"rule_id": "IR-06", "source_incident": source_incident_id, "recurrence_ref": recurrence_ref, "flagged_siblings": siblings}

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-07: Lesson Deduplication
    # -------------------------------------------------------------
    async def evaluate_ir07_lesson_deduplication(self, lesson_id: str, lesson_text: str) -> dict[str, Any] | None:
        """
        Computes cosine similarity of lesson against existing lessons.
        If similarity > 0.75, links SIMILAR_TO and sets duplicate_of.
        """
        def _exec():
            # Query existing lessons
            query_all = f"MATCH (l:Lesson) WHERE l.id <> '{lesson_id}' RETURN l.id, l.description"
            rows = self.client.query(query_all)
            if not rows:
                return None

            existing_ids = [r[0] for r in rows if r and r[1]]
            existing_texts = [r[1] for r in rows if r and r[1]]
            if not existing_texts:
                return None

            # Embed using FastEmbed
            current_emb = embed_texts([lesson_text])[0]
            existing_embs = embed_texts(existing_texts)

            best_sim = 0.0
            best_match_id = None

            import numpy as np
            v1 = np.array(current_emb)
            norm_v1 = np.linalg.norm(v1)

            for e_id, e_vec in zip(existing_ids, existing_embs):
                v2 = np.array(e_vec)
                denom = norm_v1 * np.linalg.norm(v2)
                sim = float(np.dot(v1, v2) / denom) if denom > 0 else 0.0
                if sim > best_sim:
                    best_sim = sim
                    best_match_id = e_id

            if best_sim > 0.75 and best_match_id:
                link_cypher = f"""
                MATCH (a:Lesson {{id: '{lesson_id}'}}), (b:Lesson {{id: '{best_match_id}'}})
                MERGE (a)-[r:SIMILAR_TO {{similarity: {round(best_sim, 3)}}}]->(b)
                SET a.duplicate_of = '{best_match_id}',
                    b.recurrence_count = coalesce(b.recurrence_count, 1) + 1
                """
                self.client.query(link_cypher)
                return {"rule_id": "IR-07", "lesson_id": lesson_id, "duplicate_of": best_match_id, "similarity": round(best_sim, 3)}

            return None

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-08: Graph Completeness Score
    # -------------------------------------------------------------
    def evaluate_ir08_completeness(self, entity_class: str, properties: dict[str, Any]) -> tuple[float, str]:
        req_fields = {
            "Organization": ["name", "legal_id", "domains"],
            "Person": ["full_name"],
            "Project": ["name", "status", "start_date"],
            "Incident": ["title", "severity", "start_datetime"],
            "Decision": ["title", "decision_date", "decision_type"],
            "Task": ["title", "status"],
        }.get(entity_class, ["name"])

        filled = sum(1 for f in req_fields if properties.get(f) is not None)
        score = min(round(filled / len(req_fields), 2), 1.0) if req_fields else 1.0

        if score >= 0.95:
            grade = "A"
        elif score >= 0.80:
            grade = "B"
        elif score >= 0.60:
            grade = "C"
        else:
            grade = "D"

        return score, grade

    # -------------------------------------------------------------
    # IR-09: Cascade Invalidation
    # -------------------------------------------------------------
    async def evaluate_ir09_cascade_invalidation(self, updated_node_id: str) -> list[str]:
        """
        Walks outbound causal, dependency, and derivation edges to depth 3.
        Sets downstream_recompute_needed = true and records recompute_triggered_by.
        """
        def _exec():
            cypher = f"""
            MATCH path = (root {{id: '{updated_node_id}'}})-[:CAUSED_BY|CAUSED_RECURRENCE|DEPENDS_ON|IMPLEMENTS|DERIVED_FROM*1..3]->(downstream)
            SET downstream.downstream_recompute_needed = true,
                downstream.recompute_triggered_by = '{updated_node_id}'
            RETURN DISTINCT downstream.id
            """
            rows = self.client.query(cypher)
            downstream_ids = [row[0] for row in rows if row and row[0]]

            # Also check and invalidate any KTP or summary document that DOCUMENTS this updated node
            ktp_cypher = f"""
            MATCH (ktp:Document)-[:DOCUMENTS]->(target {{id: '{updated_node_id}'}})
            WHERE ktp.document_type IN ['knowledge_transfer_package', 'ktp']
            SET ktp.downstream_recompute_needed = true,
                ktp.recompute_triggered_by = '{updated_node_id}'
            RETURN DISTINCT ktp.id
            """
            ktp_rows = self.client.query(ktp_cypher)
            ktp_ids = [r[0] for r in ktp_rows if r and r[0]]

            return list(set(downstream_ids + ktp_ids))

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # IR-10: Entity Resolution Merge
    # -------------------------------------------------------------
    async def evaluate_ir10_entity_merge(self, canonical_id: str, duplicate_id: str) -> bool:
        """
        Re-points all edges from duplicate to canonical node.
        Sets duplicate.status = 'merged', duplicate.merged_into = canonical_id.
        """
        def _exec():
            # 1. Fetch all inbound edges to duplicate
            in_rows = self.client.query(
                f"MATCH (other)-[r]->(dup {{id: '{duplicate_id}'}}) RETURN other.id, type(r)"
            )
            # 2. Fetch all outbound edges from duplicate
            out_rows = self.client.query(
                f"MATCH (dup {{id: '{duplicate_id}'}})-[r]->(other) RETURN type(r), other.id"
            )

            # 3. Delete existing edges connected to duplicate
            self.client.query(f"MATCH (dup {{id: '{duplicate_id}'}})-[r]-() DELETE r")

            # 4. Re-create inbound edges pointing to canonical
            for row in in_rows:
                if row and len(row) >= 2:
                    src_id, r_type = row[0], row[1]
                    self.client.query(
                        f"MATCH (src {{id: '{src_id}'}}), (can {{id: '{canonical_id}'}}) MERGE (src)-[r:{r_type}]->(can)"
                    )

            # 5. Re-create outbound edges pointing from canonical
            for row in out_rows:
                if row and len(row) >= 2:
                    r_type, tgt_id = row[0], row[1]
                    self.client.query(
                        f"MATCH (can {{id: '{canonical_id}'}}), (tgt {{id: '{tgt_id}'}}) MERGE (can)-[r:{r_type}]->(tgt)"
                    )

            # 6. Mark duplicate as merged
            self.client.query(
                f"MATCH (dup {{id: '{duplicate_id}'}}) SET dup.status = 'merged', dup.merged_into = '{canonical_id}', dup.is_stub = false"
            )
            return True

        return await run_in_threadpool(_exec)

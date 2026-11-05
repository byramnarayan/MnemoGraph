from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.user import User
from app.schemas.incident_interconnect import (
    IncidentInterconnectResponse,
    IncidentSummaryItem,
    Layer0IncidentHeader,
    Layer1ImmediateCauses,
    Layer2AffectedScope,
    Layer3CorrectiveTasks,
    Layer4RecurrenceChain,
    Layer5PeopleInvolved,
    Layer6Documents,
    Layer7LessonsLearned,
    Layer8SimilarIncidents,
)
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.memory.memory_write_service import MemoryWriteService
from app.services.vector.embeddings import embed_query
from app.services.vector.qdrant_client import QdrantService

logger = logging.getLogger(__name__)

CLEARANCE_RANKS = {
    "Public": 1,
    "Internal": 2,
    "Confidential": 3,
    "Restricted": 4,
}


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


class IncidentInterconnectService:
    """
    UKGOE Phase 10: Incident Interconnect View Service.
    Builds access-controlled, 9-layer subgraph expansion (Layers 0 through 8)
    for any selected Incident node, and updates non-destructive view metrics & episodic memory.
    """

    def __init__(
        self,
        falkor_client: FalkorDBClient | None = None,
        qdrant_service: QdrantService | None = None,
        memory_writer: MemoryWriteService | None = None,
    ):
        self.client = falkor_client or FalkorDBClient()
        self.qdrant = qdrant_service or QdrantService()
        self.memory_writer = memory_writer or MemoryWriteService()

    # -------------------------------------------------------------
    # 1. Access Policy Evaluation
    # -------------------------------------------------------------
    async def evaluate_incident_view_policy(self, user: User, incident_id: str) -> tuple[int, str]:
        """
        Evaluates INCIDENT_VIEW_ACCESS_POLICY:
        - Level 1 (Full: Layers 0-8): Admin OR manages any involved Person in Layer 5 (1-2 hops).
        - Level 2 (Team: Layers 0-6): Member of same Group as any Person in Layer 5 OR assigned to Layer 3 Task.
        - Level 3 (Summary: Layers 0-3): Any authenticated organization user.
        Returns: (access_level, description)
        """
        def _exec() -> tuple[int, str]:
            role = (user.role or "").strip().lower()
            clearance = (user.clearance_level or "Internal").capitalize()
            is_super = getattr(user, "is_superuser", False)

            # Rule 1: Admin bypass -> Level 1
            if role in ("executive admin", "admin", "system_admin") or is_super or clearance == "Restricted":
                return 1, "Level 1 (Full Access): System Administrator privilege"

            req_pid = user.person_entity_id
            if not req_pid:
                # Check graph by email or name
                clean_email = _safe_str(user.email)
                res = self.client.query(
                    f"MATCH (p:Person) WHERE p.email = '{clean_email}' OR p.name = '{_safe_str(user.full_name)}' RETURN p.id LIMIT 1"
                )
                if res and res[0]:
                    req_pid = res[0][0]

            if not req_pid:
                return 3, "Level 3 (Summary View): Authenticated member without graph persona"

            safe_inc = _safe_str(incident_id)
            safe_req = _safe_str(req_pid)

            # Rule 2: Check if requestor MANAGES any Person involved in Layer 5 (directly or within 2 hops)
            mgr_cypher = f"""
            MATCH (mgr:Person {{id: '{safe_req}'}})-[:MANAGES*1..2]->(involved:Person)
            WHERE (involved)<-[:ASSIGNED_TO]-(:Task)-[:RAISED_FROM]->(:Incident {{id: '{safe_inc}'}})
               OR (involved)<-[:AUTHORED_BY|MADE_BY]-(:Decision)-[:CAUSED_BY]->(:Incident {{id: '{safe_inc}'}})
               OR (involved)-[:LEADS]->(:Project)-[:LINKED_TO_PROJECT]-(:Incident {{id: '{safe_inc}'}})
            RETURN count(involved)
            """
            mgr_res = self.client.query(mgr_cypher)
            if mgr_res and mgr_res[0] and mgr_res[0][0] > 0:
                return 1, "Level 1 (Full Access): Organizational Manager of personnel involved in incident"

            # Rule 3: Check if requestor is MEMBER_OF same Group as any involved Person OR ASSIGNED_TO a corrective Task
            team_cypher = f"""
            MATCH (req:Person {{id: '{safe_req}'}})-[:MEMBER_OF]->(g:Group)<-[:MEMBER_OF]-(involved:Person)
            WHERE (involved)<-[:ASSIGNED_TO]-(:Task)-[:RAISED_FROM]->(:Incident {{id: '{safe_inc}'}})
               OR (involved)<-[:AUTHORED_BY|MADE_BY]-(:Decision)-[:CAUSED_BY]->(:Incident {{id: '{safe_inc}'}})
               OR (involved)-[:LEADS]->(:Project)-[:LINKED_TO_PROJECT]-(:Incident {{id: '{safe_inc}'}})
            RETURN count(involved)
            """
            team_res = self.client.query(team_cypher)
            if team_res and team_res[0] and team_res[0][0] > 0:
                return 2, "Level 2 (Team & Contributor View): Shares group membership with involved personnel"

            # Check Task assignment
            task_cypher = f"""
            MATCH (t:Task)-[:RAISED_FROM]->(inc:Incident {{id: '{safe_inc}'}})
            MATCH (t)-[:ASSIGNED_TO]->(req:Person {{id: '{safe_req}'}})
            RETURN count(t)
            """
            task_res = self.client.query(task_cypher)
            if task_res and task_res[0] and task_res[0][0] > 0:
                return 2, "Level 2 (Team & Contributor View): Assigned corrective task owner"

            return 3, "Level 3 (Summary View): General authenticated organization access"

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # 2. List Incidents for Quick Selection
    # -------------------------------------------------------------
    async def list_recent_incidents(self, limit: int = 50) -> list[IncidentSummaryItem]:
        """
        Lists incidents sorted by view_count and last_viewed_at.
        """
        def _exec() -> list[IncidentSummaryItem]:
            cypher = f"""
            MATCH (inc:Incident)
            RETURN inc.id, coalesce(inc.title, inc.name, inc.id), inc.severity, inc.type,
                   inc.status, inc.cause_status, coalesce(inc.data_quality_grade, 'B'),
                   coalesce(inc.view_count, 0), inc.last_viewed_at
            ORDER BY coalesce(inc.view_count, 0) DESC, inc.last_viewed_at DESC
            LIMIT {limit}
            """
            rows = self.client.query(cypher)
            res = []
            for r in rows:
                if not r or not r[0]:
                    continue
                res.append(
                    IncidentSummaryItem(
                        incident_id=str(r[0]),
                        title=str(r[1]),
                        severity=str(r[2]) if r[2] is not None else None,
                        type=str(r[3]) if r[3] is not None else None,
                        status=str(r[4]) if r[4] is not None else "open",
                        cause_status=str(r[5]) if r[5] is not None else None,
                        data_quality_grade=str(r[6] or "B"),
                        view_count=int(r[7] or 0),
                        last_viewed_at=str(r[8]) if r[8] is not None else None,
                    )
                )
            return res

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # 3. 9-Layer Subgraph Traversal
    # -------------------------------------------------------------
    async def build_incident_interconnect_view(
        self,
        incident_id: str,
        user: User,
        access_level: int,
    ) -> IncidentInterconnectResponse:
        """
        Constructs the multi-layer interconnected view according to access level (1, 2, or 3)
        and caller clearance level.
        """
        def _exec() -> IncidentInterconnectResponse:
            safe_id = _safe_str(incident_id)
            user_clearance = getattr(user, "clearance_level", "Internal") or "Internal"
            user_rank = CLEARANCE_RANKS.get(user_clearance.capitalize(), 2)

            # =========================================================
            # Layer 0: THE INCIDENT ITSELF
            # =========================================================
            cypher_l0 = f"MATCH (inc:Incident {{id: '{safe_id}'}}) RETURN properties(inc)"
            rows_l0 = self.client.query(cypher_l0)
            if not rows_l0 or not rows_l0[0]:
                raise ValueError(f"Incident '{incident_id}' not found in Knowledge Graph")

            p = rows_l0[0][0] or {}
            layer0 = Layer0IncidentHeader(
                incident_id=incident_id,
                title=p.get("title") or p.get("name") or incident_id,
                severity=p.get("severity"),
                type=p.get("type"),
                status=p.get("status"),
                cause_status=p.get("cause_status"),
                confirmed_cause=p.get("confirmed_cause"),
                initial_suspected_cause=p.get("initial_suspected_cause"),
                cause_revision_note=p.get("cause_revision_note"),
                is_misdiagnosed=bool(p.get("is_mis_diagnosed", False)),
                recurrence_risk=bool(p.get("recurrence_risk", False)),
                recurrence_count=int(p.get("recurrence_count", 0)),
                causal_chain_depth=int(p.get("causal_chain_depth", 0)),
                data_quality_grade=p.get("data_quality_grade", "B"),
                classification=p.get("classification", "Internal"),
                view_count=int(p.get("view_count", 0)),
                last_viewed_at=p.get("last_viewed_at"),
            )

            # =========================================================
            # Layer 1: IMMEDIATE CAUSES (Permitted: Levels 1, 2, 3)
            # =========================================================
            layer1 = None
            if access_level in (1, 2, 3):
                # Cause Decisions
                d_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})<-[:CAUSED_BY]-(dec:Decision)
                OPTIONAL MATCH (dec)-[:AUTHORED_BY|MADE_BY]->(p:Person)
                RETURN dec.id, dec.title, dec.outcome, dec.root_cause_analysis, p.name, dec.classification
                """
                d_rows = self.client.query(d_cypher)
                decisions = []
                for dr in d_rows:
                    if CLEARANCE_RANKS.get(str(dr[5] or "Internal").capitalize(), 2) <= user_rank:
                        decisions.append({
                            "decision_id": dr[0],
                            "title": dr[1],
                            "outcome": dr[2],
                            "root_cause_analysis": dr[3],
                            "made_by": dr[4],
                        })

                # Cause Changes
                c_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})<-[:CAUSED_BY]-(chg:Change)
                OPTIONAL MATCH (chg)-[:AUTHORED_BY|OWNED_BY]->(p:Person)
                RETURN chg.id, chg.change_type, chg.status, chg.affected_systems, p.name
                """
                c_rows = self.client.query(c_cypher)
                changes = [{
                    "change_id": cr[0],
                    "change_type": cr[1],
                    "status": cr[2],
                    "affected_systems": cr[3],
                    "owner": cr[4],
                } for cr in c_rows]

                # Prior Incidents in cause set
                pi_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})<-[:CAUSED_BY]-(pi:Incident)
                RETURN pi.id, pi.title, pi.severity
                """
                pi_rows = self.client.query(pi_cypher)
                prior_inc = [{"incident_id": pir[0], "title": pir[1], "severity": pir[2]} for pir in pi_rows]

                # Linked Project
                lp_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})-[:LINKED_TO_PROJECT]->(pr:Project)
                RETURN pr.id, pr.name, pr.status
                LIMIT 1
                """
                lp_rows = self.client.query(lp_cypher)
                linked_proj = {"project_id": lp_rows[0][0], "name": lp_rows[0][1], "status": lp_rows[0][2]} if lp_rows and lp_rows[0] else None

                layer1 = Layer1ImmediateCauses(
                    cause_decisions=decisions,
                    cause_changes=changes,
                    prior_incidents=prior_inc,
                    linked_project=linked_proj,
                )

            # =========================================================
            # Layer 2: AFFECTED SCOPE (Permitted: Levels 1, 2, 3)
            # =========================================================
            layer2 = None
            if access_level in (1, 2, 3):
                # Affected Systems
                sys_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})-[:AFFECTS]->(sys:System)
                RETURN sys.id, sys.name, sys.status, sys.criticality
                """
                sys_rows = self.client.query(sys_cypher)
                affected_systems = [{
                    "system_id": sr[0],
                    "name": sr[1],
                    "status": sr[2],
                    "criticality": sr[3],
                } for sr in sys_rows]

                # Affected Locations
                loc_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})-[:AFFECTS]->(loc:Location)
                RETURN loc.id, loc.name, loc.region
                """
                loc_rows = self.client.query(loc_cypher)
                affected_locations = [{
                    "location_id": lr[0],
                    "name": lr[1],
                    "region": lr[2],
                } for lr in loc_rows]

                # Project context & Milestones
                proj_ctx = None
                pm_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})-[:LINKED_TO_PROJECT]->(proj:Project)
                OPTIONAL MATCH (proj)-[:PART_OF|DEPENDS_ON]->(m:Milestone)
                WHERE m.status IN ['delayed', 'pending', 'in_progress']
                RETURN proj.id, proj.name, proj.status, m.id, m.name, m.status
                """
                pm_rows = self.client.query(pm_cypher)
                if pm_rows and pm_rows[0]:
                    delayed_milestones = []
                    for mr in pm_rows:
                        if mr[3]:
                            delayed_milestones.append({"milestone_id": mr[3], "name": mr[4], "status": mr[5]})
                    proj_ctx = {
                        "project_id": pm_rows[0][0],
                        "name": pm_rows[0][1],
                        "status": pm_rows[0][2],
                        "delayed_milestones": delayed_milestones,
                    }

                layer2 = Layer2AffectedScope(
                    affected_systems=affected_systems,
                    affected_locations=affected_locations,
                    linked_project_context=proj_ctx,
                )

            # =========================================================
            # Layer 3: TASKS AND CORRECTIVE ACTIONS (Permitted: Levels 1, 2, 3)
            # =========================================================
            layer3 = None
            if access_level in (1, 2, 3):
                t_cypher = f"""
                MATCH (task:Task)-[:RAISED_FROM|CAUSED_BY|RESOLVED_BY|PREVENTED_BY]-(inc:Incident {{id: '{safe_id}'}})
                OPTIONAL MATCH (task)-[:ASSIGNED_TO]->(p:Person)
                OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
                RETURN task.id, task.title, task.status, task.due_date, task.completion_date,
                       task.days_overdue, task.effectiveness_label, task.recurrence_ref,
                       task.classification, p.id, coalesce(p.full_name, p.name, p.id), g.name, p.employment_status
                """
                t_rows = self.client.query(t_cypher)
                tasks = []
                for tr in t_rows:
                    t_cls = tr[8] or "Internal"
                    if CLEARANCE_RANKS.get(str(t_cls).capitalize(), 2) > user_rank:
                        continue
                    assigned = {
                        "person_id": tr[9],
                        "name": tr[10],
                        "group": tr[11],
                        "employment_status": tr[12],
                    } if tr[9] else None

                    tasks.append({
                        "task_id": tr[0],
                        "title": tr[1],
                        "status": tr[2] or "open",
                        "due_date": tr[3],
                        "completion_date": tr[4],
                        "days_overdue": tr[5],
                        "effectiveness_label": tr[6] or "pending",
                        "recurrence_ref": tr[7],
                        "assigned_person": assigned,
                        "classification": t_cls,
                    })

                # Sort tasks: overdue first, in_progress, open, completed
                status_order = {"overdue": 0, "in_progress": 1, "open": 2, "completed": 3, "done": 4}
                tasks.sort(key=lambda x: status_order.get(str(x.get("status", "")).lower(), 5))

                layer3 = Layer3CorrectiveTasks(tasks=tasks)

            # =========================================================
            # Layer 4: RECURRENCE CHAIN (Permitted: Levels 1, 2)
            # =========================================================
            layer4 = None
            if access_level in (1, 2):
                # Backward recurrence: prior incident that caused recurrence of this incident
                back_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})<-[:CAUSED_RECURRENCE]-(prior:Incident)
                OPTIONAL MATCH (ineff:Task)-[:RAISED_FROM]->(prior) WHERE ineff.effectiveness_label = 'ineffective'
                RETURN prior.id, prior.title, prior.severity, ineff.id
                """
                b_rows = self.client.query(back_cypher)
                backward = [{
                    "prior_incident_id": br[0],
                    "title": br[1],
                    "severity": br[2],
                    "ineffective_task_id": br[3],
                } for br in b_rows]

                # Forward recurrence: downstream incident caused by this incident
                fwd_cypher = f"""
                MATCH (inc:Incident {{id: '{safe_id}'}})-[:CAUSED_RECURRENCE]->(subsequent:Incident)
                RETURN subsequent.id, subsequent.title, subsequent.severity, subsequent.created_at
                """
                f_rows = self.client.query(fwd_cypher)
                forward = [{
                    "subsequent_incident_id": fr[0],
                    "title": fr[1],
                    "severity": fr[2],
                    "created_at": fr[3],
                } for fr in f_rows]

                layer4 = Layer4RecurrenceChain(
                    backward_recurrence=backward,
                    forward_recurrence=forward,
                )

            # =========================================================
            # Layer 5: PEOPLE INVOLVED (Permitted: Levels 1, 2)
            # =========================================================
            layer5 = None
            if access_level in (1, 2):
                # Privacy redaction check: Redact if caller is not Manager/Admin/HR
                is_privileged = (
                    access_level == 1
                    or user_rank >= 3
                    or "hr" in (user.role or "").lower()
                    or "hr" in (user.department or "").lower()
                )

                def _format_person(pid, name, role, grp, emp_status, email):
                    if not is_privileged:
                        return {
                            "person_id": pid,
                            "name": name,
                            "group": grp,
                            "role": "[Redacted]",
                            "employment_status": emp_status,
                            "email": "[Redacted]",
                            "is_redacted": True,
                        }
                    return {
                        "person_id": pid,
                        "name": name,
                        "group": grp,
                        "role": role,
                        "employment_status": emp_status,
                        "email": email,
                        "is_redacted": False,
                    }

                # 1. Task Assignees
                ta_cypher = f"""
                MATCH (p:Person)<-[:ASSIGNED_TO]-(t:Task)-[:RAISED_FROM]->(inc:Incident {{id: '{safe_id}'}})
                OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
                RETURN DISTINCT p.id, coalesce(p.full_name, p.name, p.id), p.role, g.name, p.employment_status, p.email
                """
                ta_rows = self.client.query(ta_cypher)
                task_assignees = [_format_person(*r) for r in ta_rows if r and r[0]]

                # 2. Decision Makers
                dm_cypher = f"""
                MATCH (p:Person)<-[:AUTHORED_BY|MADE_BY]-(dec:Decision)-[:CAUSED_BY]->(inc:Incident {{id: '{safe_id}'}})
                OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
                RETURN DISTINCT p.id, coalesce(p.full_name, p.name, p.id), p.role, g.name, p.employment_status, p.email
                """
                dm_rows = self.client.query(dm_cypher)
                decision_makers = [_format_person(*r) for r in dm_rows if r and r[0]]

                # 3. Project Leads
                pl_cypher = f"""
                MATCH (p:Person)-[:LEADS]->(proj:Project)-[:LINKED_TO_PROJECT]-(inc:Incident {{id: '{safe_id}'}})
                OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
                RETURN DISTINCT p.id, coalesce(p.full_name, p.name, p.id), p.role, g.name, p.employment_status, p.email
                """
                pl_rows = self.client.query(pl_cypher)
                project_leads = [_format_person(*r) for r in pl_rows if r and r[0]]

                layer5 = Layer5PeopleInvolved(
                    task_assignees=task_assignees,
                    decision_makers=decision_makers,
                    project_leads=project_leads,
                )

            # =========================================================
            # Layer 6: DOCUMENTS (Permitted: Levels 1, 2)
            # =========================================================
            layer6 = None
            if access_level in (1, 2):
                doc_cypher = f"""
                MATCH (doc:Document)-[:DOCUMENTS]->(inc:Incident {{id: '{safe_id}'}})
                OPTIONAL MATCH (doc)-[:AUTHORED_BY]->(p:Person)
                OPTIONAL MATCH (doc)-[:SUPERSEDED_BY]->(succ:Document)
                RETURN doc.id, doc.title, doc.document_type, doc.status, doc.creation_date,
                       doc.classification, p.name, succ.id
                """
                doc_rows = self.client.query(doc_cypher)
                documents = []
                for dr in doc_rows:
                    d_cls = dr[5] or "Internal"
                    if CLEARANCE_RANKS.get(str(d_cls).capitalize(), 2) <= user_rank:
                        documents.append({
                            "document_id": dr[0],
                            "title": dr[1],
                            "document_type": dr[2],
                            "status": dr[3],
                            "creation_date": dr[4],
                            "classification": d_cls,
                            "author": dr[6],
                            "successor_document_id": dr[7],
                        })
                layer6 = Layer6Documents(documents=documents)

            # =========================================================
            # Layer 7: LESSONS LEARNED (Permitted: Level 1)
            # =========================================================
            layer7 = None
            if access_level == 1:
                les_cypher = f"""
                MATCH (les:Lesson)-[:DERIVED_FROM|RESOLVED_BY|PREVENTED_BY]->(inc:Incident {{id: '{safe_id}'}})
                RETURN les.id, coalesce(les.title, les.name, les.id), les.summary, les.recurrence_count, les.duplicate_of
                """
                les_rows = self.client.query(les_cypher)
                lessons = [{
                    "lesson_id": lr[0],
                    "title": lr[1],
                    "summary": lr[2],
                    "recurrence_count": lr[3] or 0,
                    "duplicate_of": lr[4],
                } for lr in les_rows]
                layer7 = Layer7LessonsLearned(lessons=lessons)

            # =========================================================
            # Layer 8: SIMILAR INCIDENTS (Permitted: Level 1)
            # =========================================================
            layer8 = None
            if access_level == 1:
                similar_list = []
                try:
                    query_text = f"{layer0.title} {layer0.confirmed_cause or ''} {layer0.type or ''}".strip()
                    q_vec = embed_query(query_text)

                    # Query Qdrant
                    q_results = self.qdrant.client.query_points(
                        collection_name=self.qdrant.collection_name,
                        query=q_vec,
                        limit=6,
                    ).points

                    for pt in q_results:
                        p_eid = pt.payload.get("entity_id") or pt.payload.get("id") or str(pt.id)
                        if p_eid == incident_id:
                            continue

                        # Fetch preventative tasks for this similar incident from FalkorDB
                        prev_tasks_res = self.client.query(f"""
                        MATCH (t:Task)-[:RAISED_FROM]->(other:Incident {{id: '{_safe_str(p_eid)}'}})
                        WHERE t.effectiveness_label = 'effective' OR t.status IN ['completed', 'done']
                        RETURN t.id, t.title
                        LIMIT 3
                        """)
                        prev_tasks = [{"task_id": r[0], "title": r[1]} for r in prev_tasks_res]

                        similar_list.append({
                            "incident_id": p_eid,
                            "title": pt.payload.get("label") or pt.payload.get("title") or p_eid,
                            "severity": pt.payload.get("severity", "P2"),
                            "similarity_score": round(float(pt.score), 4),
                            "resolved_by_tasks": prev_tasks,
                        })
                        if len(similar_list) >= 5:
                            break
                except Exception as ex:
                    logger.debug(f"Layer 8 Qdrant similarity lookup fallback: {ex}")
                    # Fallback to FalkorDB type/severity matching
                    fb_cypher = f"""
                    MATCH (other:Incident)
                    WHERE other.id <> '{safe_id}' AND other.type = '{_safe_str(layer0.type)}'
                    RETURN other.id, other.title, other.severity
                    LIMIT 3
                    """
                    fb_rows = self.client.query(fb_cypher)
                    for fbr in fb_rows:
                        similar_list.append({
                            "incident_id": fbr[0],
                            "title": fbr[1],
                            "severity": fbr[2],
                            "similarity_score": 0.85,
                            "resolved_by_tasks": [],
                        })

                layer8 = Layer8SimilarIncidents(similar_incidents=similar_list)

            desc = {
                1: "Level 1: Full View (Layers 0-8 with Vector Similarity)",
                2: "Level 2: Team & Contributor View (Layers 0-6)",
                3: "Level 3: Public Summary View (Layers 0-3)",
            }.get(access_level, "Level 3: Public Summary View")

            return IncidentInterconnectResponse(
                incident_id=incident_id,
                access_level=access_level,
                access_level_description=desc,
                user_clearance=user_clearance,
                layer0_incident=layer0,
                layer1_causes=layer1,
                layer2_affected_scope=layer2,
                layer3_tasks=layer3,
                layer4_recurrence=layer4,
                layer5_people=layer5,
                layer6_documents=layer6,
                layer7_lessons=layer7,
                layer8_similar_incidents=layer8,
            )

        return await run_in_threadpool(_exec)

    # -------------------------------------------------------------
    # 4. Episodic Memory & View Metrics Logging
    # -------------------------------------------------------------
    async def record_view_access(
        self,
        incident_id: str,
        user: User,
        view_response: IncidentInterconnectResponse,
        db: AsyncSession,
    ) -> None:
        """
        Non-destructive view access recording:
        1. Increments incident_node.view_count += 1 and sets last_viewed_at = now().
        2. Writes an :EpisodeMemory node via MemoryWriteService and links [:TOUCHED] edges.
        """
        def _increment_metrics() -> int:
            now_iso = datetime.now(timezone.utc).isoformat()
            safe_id = _safe_str(incident_id)
            cypher = f"""
            MATCH (inc:Incident {{id: '{safe_id}'}})
            SET inc.view_count = coalesce(inc.view_count, 0) + 1,
                inc.last_viewed_at = '{now_iso}'
            RETURN inc.view_count
            """
            rows = self.client.query(cypher)
            return rows[0][0] if rows and rows[0] else 1

        new_count = await run_in_threadpool(_increment_metrics)
        view_response.layer0_incident.view_count = new_count
        view_response.layer0_incident.last_viewed_at = datetime.now(timezone.utc).isoformat()

        # Collect touched IDs for episodic recall
        touched: set[str] = {incident_id}
        if view_response.layer1_causes:
            for d in view_response.layer1_causes.cause_decisions:
                touched.add(d["decision_id"])
            for c in view_response.layer1_causes.cause_changes:
                touched.add(c["change_id"])
            if view_response.layer1_causes.linked_project:
                touched.add(view_response.layer1_causes.linked_project["project_id"])
        if view_response.layer2_affected_scope:
            for s in view_response.layer2_affected_scope.affected_systems:
                touched.add(s["system_id"])
            for l in view_response.layer2_affected_scope.affected_locations:
                touched.add(l["location_id"])
        if view_response.layer3_tasks:
            for t in view_response.layer3_tasks.tasks:
                touched.add(t["task_id"])
        if view_response.layer5_people:
            for p in view_response.layer5_people.task_assignees:
                touched.add(p["person_id"])
            for p in view_response.layer5_people.decision_makers:
                touched.add(p["person_id"])
        if view_response.layer6_documents:
            for doc in view_response.layer6_documents.documents:
                touched.add(doc["document_id"])

        try:
            session_id = f"incident_view_{incident_id}_{uuid.uuid4().hex[:6]}"
            await self.memory_writer.record_ukgoe_interaction(
                db=db,
                session_id=session_id,
                user_id=user.id,
                query=f"Incident Interconnect View: {view_response.layer0_incident.title} ({incident_id})",
                answer=f"Accessed multi-layer interconnect view under Access Level {view_response.access_level}",
                confidence_score=1.0,
                entity_ids_touched=list(touched),
            )
        except Exception as e:
            logger.warning(f"Error recording episodic memory for incident view: {e}")


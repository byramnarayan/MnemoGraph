from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.schemas.ktp import (
    KnowledgeTransferPackageResponse,
    SectionAPersonProfile,
    SectionBActiveOwnership,
    SectionCDecisionHistory,
    SectionDIncidentInvolvement,
    SectionEKnowledgeAuthored,
    SectionFRiskFlags,
    SectionGHandoverRecommendations,
    SuccessorCandidate,
)
from app.services.graph.falkordb_client import FalkorDBClient

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


class KTPBuilder:
    """
    Constructs Sections A through G via read-only openCypher traversals
    with dynamic clearance filtering and role scoping.
    """

    def __init__(self, client: FalkorDBClient):
        self.client = client

    async def build(
        self,
        target_person_id: str,
        requestor_id: str,
        requestor_role: str,
        user_clearance: str = "Internal",
    ) -> KnowledgeTransferPackageResponse:
        def _exec() -> KnowledgeTransferPackageResponse:
            pid = _safe_str(target_person_id)
            user_rank = CLEARANCE_RANKS.get(user_clearance.capitalize(), 2)
            referenced_ids: set[str] = set()

            # --- Target Person Info ---
            p_cypher = f"""
            MATCH (p:Person {{id: '{pid}'}})
            OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
            OPTIONAL MATCH (p)-[:LOCATED_AT]->(loc:Location)
            RETURN properties(p), g.name, loc.name
            """
            p_rows = self.client.query(p_cypher)
            if not p_rows or not p_rows[0]:
                raise ValueError(f"Person entity '{target_person_id}' not found in Knowledge Graph")

            p_props = p_rows[0][0] or {}
            group_name = p_rows[0][1] or p_props.get("department")
            loc_name = p_rows[0][2] or p_props.get("location")
            person_name = p_props.get("full_name") or p_props.get("name") or target_person_id
            referenced_ids.add(target_person_id)

            skills_raw = p_props.get("skills", [])
            if isinstance(skills_raw, str):
                skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
            elif isinstance(skills_raw, list):
                skills = [str(s) for s in skills_raw]
            else:
                skills = []

            # SECTION A: Profile
            section_a: SectionAPersonProfile | None = None
            if requestor_role in ("admin", "manager", "hr", "peer_senior"):
                role_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[r:HELD_ROLE]->(rl:Role)
                RETURN rl.title, r.start_date, r.end_date, coalesce(rl.department, '')
                """
                role_rows = self.client.query(role_cypher)
                role_history = [
                    {"title": rr[0], "start_date": rr[1], "end_date": rr[2], "department": rr[3]}
                    for rr in role_rows
                ]

                mgr_chain = []
                if requestor_role != "hr":
                    mgr_cypher = f"""
                    MATCH path = (m:Person)-[:MANAGES*1..5]->(p:Person {{id: '{pid}'}})
                    RETURN m.id, coalesce(m.full_name, m.name, m.id), m.role, length(path) as depth
                    ORDER BY depth ASC
                    """
                    mgr_rows = self.client.query(mgr_cypher)
                    for mr in mgr_rows:
                        mgr_chain.append({
                            "manager_id": mr[0],
                            "name": mr[1],
                            "role": mr[2],
                            "depth": mr[3],
                        })
                        referenced_ids.add(mr[0])

                section_a = SectionAPersonProfile(
                    person_id=target_person_id,
                    full_name=person_name,
                    current_role=p_props.get("role") or p_props.get("title"),
                    current_group=group_name,
                    location=loc_name,
                    role_history=role_history,
                    manager_chain=mgr_chain,
                    skills=skills,
                )

            # SECTION B: Active Ownership
            section_b: SectionBActiveOwnership | None = None
            active_projects = []
            active_tasks = []

            if requestor_role in ("admin", "manager", "peer_senior"):
                proj_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[r:LEADS|CONTRIBUTES_TO|MEMBER_OF]-(proj:Project)
                RETURN proj.id, proj.name, type(r), proj.status, proj.classification
                """
                proj_rows = self.client.query(proj_cypher)
                for pr in proj_rows:
                    proj_id, proj_name, rel_type, p_status, p_class = pr[0], pr[1], pr[2], pr[3] or "active", pr[4] or "Internal"
                    if CLEARANCE_RANKS.get(p_class.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(proj_id)

                    m_cypher = f"""
                    MATCH (proj:Project {{id: '{proj_id}'}})-[:PART_OF|DEPENDS_ON|IMPLEMENTS]-(m:Milestone)
                    RETURN m.id, m.name, m.status, m.target_date
                    """
                    m_rows = self.client.query(m_cypher)
                    milestones = [{"id": mr[0], "name": mr[1], "status": mr[2], "target_date": mr[3]} for mr in m_rows]
                    for mr in m_rows:
                        referenced_ids.add(mr[0])

                    d_cypher = f"""
                    MATCH (proj:Project {{id: '{proj_id}'}})-[:LINKED_TO_PROJECT|AFFECTS|IMPLEMENTS]-(dec:Decision)
                    RETURN dec.id, dec.title, dec.outcome
                    """
                    d_rows = self.client.query(d_cypher)
                    decisions = [{"id": dr[0], "title": dr[1], "outcome": dr[2]} for dr in d_rows]
                    for dr in d_rows:
                        referenced_ids.add(dr[0])

                    i_cypher = f"""
                    MATCH (proj:Project {{id: '{proj_id}'}})-[:LINKED_TO_PROJECT|AFFECTS]-(inc:Incident)
                    RETURN inc.id, inc.title, inc.severity
                    """
                    i_rows = self.client.query(i_cypher)
                    incidents = [{"id": ir[0], "title": ir[1], "severity": ir[2]} for ir in i_rows]
                    for ir in i_rows:
                        referenced_ids.add(ir[0])

                    active_projects.append({
                        "project_id": proj_id,
                        "name": proj_name,
                        "relationship": rel_type,
                        "status": p_status,
                        "milestones": milestones,
                        "linked_decisions": decisions,
                        "linked_incidents": incidents,
                    })

                task_cypher = f"""
                MATCH (task:Task)-[:ASSIGNED_TO]-(p:Person {{id: '{pid}'}})
                OPTIONAL MATCH (task)-[:RAISED_FROM|CAUSED_BY|TRIGGERED|FOLLOWED_BY]-(src)
                RETURN task.id, task.title, task.status, task.due_date, task.effectiveness_label,
                       task.classification, src.id, labels(src)
                """
                task_rows = self.client.query(task_cypher)
                for tr in task_rows:
                    t_id, t_title, t_status, t_due, t_eff, t_class, s_id, s_lbl = tr[0], tr[1], tr[2] or "open", tr[3], tr[4], tr[5] or "Internal", tr[6], tr[7]
                    if CLEARANCE_RANKS.get(t_class.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(t_id)
                    if s_id:
                        referenced_ids.add(s_id)

                    active_tasks.append({
                        "task_id": t_id,
                        "title": t_title,
                        "status": t_status,
                        "due_date": t_due,
                        "effectiveness_label": t_eff,
                        "source_entity": {"id": s_id, "labels": s_lbl} if s_id else None,
                    })

                section_b = SectionBActiveOwnership(
                    active_projects=active_projects,
                    active_tasks=active_tasks,
                )

            # SECTION C: Decision History
            section_c: SectionCDecisionHistory | None = None
            if requestor_role in ("admin", "manager", "peer_senior"):
                dec_cypher = f"""
                MATCH (dec:Decision)-[:AUTHORED_BY|MADE_BY|DECIDED_BY]-(p:Person {{id: '{pid}'}})
                OPTIONAL MATCH (dec)-[:LINKED_TO_PROJECT]-(proj:Project)
                OPTIONAL MATCH (t:Task)-[:RAISED_FROM]-(dec) WHERE t.status IN ['open', 'in_progress']
                RETURN dec.id, dec.title, dec.outcome, dec.decision_type, dec.decision_date,
                       dec.root_cause_analysis, dec.classification, proj.status, count(t)
                """
                dec_rows = self.client.query(dec_cypher)
                decisions_made = []
                for dr in dec_rows:
                    d_id, d_title, d_out, d_type, d_date, d_rca, d_class, p_stat, open_t = dr[0], dr[1], dr[2], dr[3], dr[4], dr[5], dr[6] or "Internal", dr[7], dr[8]
                    if CLEARANCE_RANKS.get(d_class.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(d_id)
                    decisions_made.append({
                        "decision_id": d_id,
                        "title": d_title,
                        "outcome": d_out,
                        "decision_type": d_type,
                        "decision_date": d_date,
                        "root_cause_analysis": d_rca if requestor_role != "peer_senior" else None,
                        "linked_project_status": p_stat,
                        "open_tasks_count": open_t,
                    })

                contrib_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[:CONTRIBUTES_TO|LEADS]-(proj:Project)-[:LINKED_TO_PROJECT|AFFECTS]-(dec:Decision)
                RETURN DISTINCT dec.id, dec.title, dec.outcome, proj.name, dec.classification
                """
                contrib_rows = self.client.query(contrib_cypher)
                decisions_contrib = []
                for cr in contrib_rows:
                    cd_id, cd_title, cd_out, pr_name, cd_class = cr[0], cr[1], cr[2], cr[3], cr[4] or "Internal"
                    if CLEARANCE_RANKS.get(cd_class.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(cd_id)
                    decisions_contrib.append({
                        "decision_id": cd_id,
                        "title": cd_title,
                        "outcome": cd_out,
                        "project_name": pr_name,
                    })

                section_c = SectionCDecisionHistory(
                    decisions_made=decisions_made,
                    decisions_contributed=decisions_contrib,
                )

            # SECTION D: Incident Involvement
            section_d: SectionDIncidentInvolvement | None = None
            if requestor_role in ("admin", "manager", "peer_senior"):
                inc_assignee_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[:ASSIGNED_TO]-(task:Task)-[:RAISED_FROM|CAUSED_BY|TRIGGERED]-(inc:Incident)
                OPTIONAL MATCH (inc)-[:DOCUMENTS|REFERENCED_BY]-(pir:Document)
                RETURN inc.id, inc.title, inc.severity, inc.type, inc.cause_status, inc.classification,
                       task.id, task.title, task.status, pir.id, pir.title
                """
                inc_rows = self.client.query(inc_assignee_cypher)
                inc_assignee_dict: dict[str, dict[str, Any]] = {}
                for ir in inc_rows:
                    i_id, i_title, i_sev, i_typ, i_cause, i_cls = ir[0], ir[1], ir[2], ir[3], ir[4], ir[5] or "Internal"
                    t_id, t_title, t_status = ir[6], ir[7], ir[8]
                    pir_id, pir_title = ir[9], ir[10]

                    if CLEARANCE_RANKS.get(i_cls.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(i_id)

                    if i_id not in inc_assignee_dict:
                        inc_assignee_dict[i_id] = {
                            "incident_id": i_id,
                            "title": i_title,
                            "severity": i_sev,
                            "type": i_typ,
                            "cause_status": i_cause,
                            "tasks": [],
                            "pir_documents": [],
                        }
                    if t_id and not any(t["task_id"] == t_id for t in inc_assignee_dict[i_id]["tasks"]):
                        inc_assignee_dict[i_id]["tasks"].append({"task_id": t_id, "title": t_title, "status": t_status})
                    if pir_id and not any(p["id"] == pir_id for p in inc_assignee_dict[i_id]["pir_documents"]):
                        inc_assignee_dict[i_id]["pir_documents"].append({"id": pir_id, "title": pir_title})
                        referenced_ids.add(pir_id)

                inc_lead_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[:LEADS]-(proj:Project)-[:LINKED_TO_PROJECT|AFFECTS]-(inc:Incident)
                RETURN inc.id, inc.title, inc.severity, inc.type, inc.cause_status, inc.classification, proj.name
                """
                inc_lead_rows = self.client.query(inc_lead_cypher)
                inc_lead = []
                for il in inc_lead_rows:
                    il_id, il_title, il_sev, il_typ, il_cause, il_cls, pr_name = il[0], il[1], il[2], il[3], il[4], il[5] or "Internal", il[6]
                    if CLEARANCE_RANKS.get(il_cls.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(il_id)
                    inc_lead.append({
                        "incident_id": il_id,
                        "title": il_title,
                        "severity": il_sev,
                        "type": il_typ,
                        "cause_status": il_cause,
                        "project_name": pr_name,
                    })

                section_d = SectionDIncidentInvolvement(
                    incidents_as_task_assignee=list(inc_assignee_dict.values()),
                    incidents_as_project_lead=inc_lead,
                )

            # SECTION E: Knowledge Authored
            section_e: SectionEKnowledgeAuthored | None = None
            authored_docs = []
            if requestor_role in ("admin", "manager", "peer_senior"):
                doc_cypher = f"""
                MATCH (doc:Document)-[:AUTHORED_BY]-(p:Person {{id: '{pid}'}})
                WHERE coalesce(doc.document_type, '') <> 'knowledge_transfer_package'
                OPTIONAL MATCH (doc)-[:SUPERSEDED_BY]->(succ:Document)
                RETURN doc.id, doc.title, doc.document_type, doc.status, doc.creation_date,
                       doc.classification, succ.id
                """
                doc_rows = self.client.query(doc_cypher)
                for dr in doc_rows:
                    d_id, d_title, d_type, d_status, d_date, d_cls, s_id = dr[0], dr[1], dr[2], dr[3], dr[4], dr[5] or "Internal", dr[6]
                    if CLEARANCE_RANKS.get(d_cls.capitalize(), 2) > user_rank:
                        continue
                    referenced_ids.add(d_id)
                    authored_docs.append({
                        "document_id": d_id,
                        "title": d_title,
                        "document_type": d_type,
                        "status": d_status,
                        "creation_date": d_date,
                        "successor_document_id": s_id,
                    })

                les_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[:LEADS]-(proj:Project)-[:DERIVED_FROM|RESOLVED_BY|PREVENTED_BY]-(les:Lesson)
                RETURN les.id, les.title, proj.id, les.summary
                """
                les_rows = self.client.query(les_cypher)
                lessons = []
                for lr in les_rows:
                    referenced_ids.add(lr[0])
                    lessons.append({
                        "lesson_id": lr[0],
                        "title": lr[1],
                        "project_id": lr[2],
                        "summary": lr[3],
                    })

                section_e = SectionEKnowledgeAuthored(
                    authored_documents=authored_docs,
                    lessons_learned=lessons,
                )

            # SECTION F: Risk Flags
            section_f: SectionFRiskFlags | None = None
            if requestor_role in ("admin", "manager", "peer_senior"):
                concentration_score = float(p_props.get("owned_critical_items", 0.0))
                if p_props.get("concentration_risk") is True and concentration_score == 0.0:
                    concentration_score = 1.0

                rec_tasks = []
                for t in active_tasks:
                    t_cypher = f"""
                    MATCH (t:Task {{id: '{t['task_id']}'}})
                    OPTIONAL MATCH (t)-[:RAISED_FROM|CAUSED_BY]-(inc:Incident)
                    RETURN t.recurrence_risk_inherited, inc.recurrence_risk
                    """
                    t_res = self.client.query(t_cypher)
                    if t_res and t_res[0]:
                        if t_res[0][0] is True or t_res[0][1] is True:
                            rec_tasks.append(t)

                overdue_tasks = [t for t in active_tasks if t.get("status") == "overdue"]

                gap_cypher = f"""
                MATCH (p:Person {{id: '{pid}'}})-[:ASSIGNED_TO|LEADS]-(item)
                WHERE item.documentation_gap = true
                RETURN item.id, coalesce(item.title, item.name, item.id), labels(item)
                """
                gap_rows = self.client.query(gap_cypher)
                doc_gaps = [{"id": gr[0], "title": gr[1], "labels": gr[2]} for gr in gap_rows]

                section_f = SectionFRiskFlags(
                    concentration_risk_score=concentration_score,
                    recurrence_risk_tasks=rec_tasks,
                    overdue_tasks=overdue_tasks,
                    documentation_gaps=doc_gaps,
                )

            # SECTION G: Recommended Handover Actions
            section_g: SectionGHandoverRecommendations | None = None
            if requestor_role in ("admin", "manager", "peer_senior"):
                tasks_to_reassign = active_tasks
                projects_needing_replacement = [
                    p for p in active_projects if p.get("relationship") == "LEADS" or len(active_projects) <= 2
                ]

                sole_author_docs = []
                for doc in authored_docs:
                    d_id = doc["document_id"]
                    author_check = f"""
                    MATCH (d:Document {{id: '{d_id}'}})-[:AUTHORED_BY]-(other:Person)
                    WHERE other.id <> '{pid}'
                    RETURN count(other)
                    """
                    a_res = self.client.query(author_check)
                    other_authors = a_res[0][0] if a_res and a_res[0] else 0
                    if other_authors == 0:
                        sole_author_docs.append(doc)

                candidates_cypher = f"""
                MATCH (cand:Person)
                WHERE cand.id <> '{pid}'
                  AND (cand.employment_status = 'active' OR cand.employment_status IS NULL)
                RETURN cand.id, coalesce(cand.full_name, cand.name, cand.id), cand.role, cand.department, cand.skills
                LIMIT 30
                """
                cand_rows = self.client.query(candidates_cypher)
                successor_candidates: list[SuccessorCandidate] = []
                target_skills_set = {s.lower() for s in skills}

                for cr in cand_rows:
                    c_id, c_name, c_role, c_grp, c_skills_raw = cr[0], cr[1], cr[2], cr[3], cr[4]
                    if isinstance(c_skills_raw, str):
                        c_skills = [s.strip() for s in c_skills_raw.split(",") if s.strip()]
                    elif isinstance(c_skills_raw, list):
                        c_skills = [str(s) for s in c_skills_raw]
                    else:
                        c_skills = []

                    shared = [s for s in c_skills if s.lower() in target_skills_set]
                    overlap_count = len(shared)
                    if overlap_count > 0 or len(cand_rows) <= 3:
                        successor_candidates.append(
                            SuccessorCandidate(
                                person_id=c_id,
                                full_name=c_name,
                                role=c_role,
                                group=c_grp,
                                shared_skills=shared,
                                skill_overlap_count=overlap_count,
                            )
                        )

                successor_candidates.sort(key=lambda x: x.skill_overlap_count, reverse=True)
                top_successors = successor_candidates[:5]

                section_g = SectionGHandoverRecommendations(
                    tasks_to_reassign=tasks_to_reassign,
                    projects_needing_lead_or_contributor=projects_needing_replacement,
                    sole_author_documents=sole_author_docs,
                    successor_candidates=top_successors,
                )

            package_classification = "Confidential" if requestor_role in ("admin", "manager") else "Internal"
            today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{target_person_id}_ktp_{today_iso}"))

            return KnowledgeTransferPackageResponse(
                doc_id=doc_uuid,
                subject_person_id=target_person_id,
                subject_person_name=person_name,
                requestor_id=requestor_id,
                requestor_role=requestor_role,
                generated_at=datetime.now(timezone.utc).isoformat(),
                classification=package_classification,
                is_stale=False,
                referenced_entity_ids=sorted(list(referenced_ids)),
                section_a_profile=section_a,
                section_b_ownership=section_b,
                section_c_decisions=section_c,
                section_d_incidents=section_d,
                section_e_knowledge=section_e,
                section_f_risks=section_f,
                section_g_handover=section_g,
            )

        return await run_in_threadpool(_exec)


from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.models.user import User
from app.schemas.ktp import (
    AssignHandoverResponse,
    KTPCandidateResponse,
    KtpPersonSummary,
)
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


class KTPDirectoryManager:
    """
    Manages personnel directory listings, candidate filtration,
    and directed handover assignments.
    """

    def __init__(self, client: FalkorDBClient):
        self.client = client

    async def list_candidates(self) -> list[KTPCandidateResponse]:
        """
        Lists all Person nodes who are inactive, on leave, terminated, or have existing KTPs.
        """
        def _exec() -> list[KTPCandidateResponse]:
            cypher = """
            MATCH (p:Person)
            WHERE p.employment_status IN ['on_leave', 'inactive', 'terminated', 'resigned', 'departing', 'departed']
               OR p.ktp_generated = true
            OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
            RETURN p.id, coalesce(p.full_name, p.name, p.id), p.role, g.name, p.employment_status,
                   p.ktp_generated, p.ktp_doc_id, p.ktp_generated_at
            LIMIT 100
            """
            rows = self.client.query(cypher)
            candidates = []
            for r in rows:
                if not r or not r[0]:
                    continue
                candidates.append(
                    KTPCandidateResponse(
                        person_id=str(r[0]),
                        full_name=str(r[1]),
                        role=str(r[2]) if r[2] is not None else None,
                        group=str(r[3]) if r[3] is not None else None,
                        employment_status=str(r[4] or "active"),
                        ktp_generated=bool(r[5]),
                        ktp_doc_id=str(r[6]) if r[6] is not None else None,
                        ktp_generated_at=str(r[7]) if r[7] is not None else None,
                    )
                )
            return candidates

        return await run_in_threadpool(_exec)

    async def list_all_personnel(self, user: User, status_filter: str | None = None) -> list[KtpPersonSummary]:
        """
        Lists personnel with role-based visibility:
        - Admin: full directory.
        - Manager: team subordinates + self + people handed over to manager.
        - Regular Member / Successor: strictly self + people handed over to them.
        """
        def _exec() -> list[KtpPersonSummary]:
            role_name = (user.role or "").strip().lower()
            clearance = (user.clearance_level or "Internal").capitalize()
            is_super = getattr(user, "is_superuser", False)
            is_admin = role_name in ("executive admin", "admin", "system_admin") or is_super or clearance == "Restricted"

            req_pid = user.person_entity_id
            if not req_pid:
                clean_email = _safe_str(user.email)
                email_res = self.client.query(
                    f"MATCH (p:Person) WHERE p.email = '{clean_email}' OR p.name = '{_safe_str(user.full_name)}' RETURN p.id LIMIT 1"
                )
                if email_res and email_res[0]:
                    req_pid = email_res[0][0]

            is_mgr = any(k in role_name for k in ["manager", "lead", "director", "vp", "head"])
            req_id_str = _safe_str(req_pid or "")

            where_clause = ""
            if not is_admin:
                if not req_id_str:
                    return []
                if is_mgr:
                    id_cypher = f"""
                    MATCH (p:Person {{id: '{req_id_str}'}}) RETURN p.id
                    UNION
                    MATCH (mgr:Person {{id: '{req_id_str}'}})-[:MANAGES*1..2]->(p:Person) RETURN p.id
                    UNION
                    MATCH (p:Person)-[r:HANDED_OVER_TO]->(mgr:Person {{id: '{req_id_str}'}}) RETURN p.id
                    """
                else:
                    id_cypher = f"""
                    MATCH (p:Person {{id: '{req_id_str}'}}) RETURN p.id
                    UNION
                    MATCH (p:Person)-[r:HANDED_OVER_TO]->(me:Person {{id: '{req_id_str}'}}) RETURN p.id
                    """
                id_rows = self.client.query(id_cypher)
                allowed_pids = [f"'{_safe_str(row[0])}'" for row in id_rows if row and row[0]]
                if not allowed_pids:
                    return []
                where_clause = f"WHERE NOT p.id STARTS WITH 'dup_' AND p.id IN [{', '.join(allowed_pids)}]"
            else:
                where_clause = "WHERE NOT p.id STARTS WITH 'dup_'"
            cypher = f"""
            MATCH (p:Person)
            {where_clause}
            OPTIONAL MATCH (p)-[:MEMBER_OF]->(g:Group)
            OPTIONAL MATCH (p)-[:LOCATED_AT]->(loc:Location)
            OPTIONAL MATCH (p)-[r_ho:HANDED_OVER_TO]->(target_me:Person {{id: '{req_id_str}'}})
            OPTIONAL MATCH (p)-[:LEADS|CONTRIBUTES_TO|MEMBER_OF]-(proj:Project)
            WITH p, coalesce(head(collect(DISTINCT g.name)), p.department, 'Operations') as g_name, coalesce(head(collect(DISTINCT loc.name)), p.location, 'HQ') as loc_name, count(r_ho) > 0 as is_ho, count(DISTINCT proj) as active_proj_count
            OPTIONAL MATCH (task:Task)-[:ASSIGNED_TO]-(p)
            RETURN p.id, coalesce(p.full_name, p.name, p.id) as display_name, p.role, g_name, loc_name,
                   coalesce(p.employment_status, 'active') as emp_status, coalesce(p.clearance_level, 'Internal') as clr,
                   coalesce(p.ktp_generated, false) as ktp_gen, p.ktp_doc_id, p.ktp_generated_at,
                   coalesce(p.concentration_risk, false) as conc_risk, active_proj_count, count(DISTINCT task) as task_cnt, is_ho
            ORDER BY ktp_gen DESC, conc_risk DESC, active_proj_count DESC, display_name ASC
            LIMIT 200
            """
            rows = self.client.query(cypher)
            results = []
            seen_pids = set()
            for r in rows:
                if not r or not r[0]:
                    continue
                pid_str = str(r[0])
                if pid_str in seen_pids:
                    continue
                seen_pids.add(pid_str)

                emp_status = str(r[5] or "active").lower()
                if status_filter:
                    sf = status_filter.lower()
                    if sf == "active" and emp_status not in ("active", "employed"):
                        continue
                    if sf in ("on_leave", "departing", "inactive") and emp_status not in ("on_leave", "inactive", "terminated", "resigned", "departing", "departed"):
                        continue
                    if sf == "handed_over" and not r[13]:
                        continue

                results.append(
                    KtpPersonSummary(
                        person_id=str(r[0]),
                        full_name=str(r[1]),
                        role=str(r[2]) if r[2] is not None else None,
                        group=str(r[3]) if r[3] is not None else None,
                        location=str(r[4]) if r[4] is not None else None,
                        employment_status=str(r[5] or "active"),
                        clearance_level=str(r[6] or "Internal"),
                        ktp_generated=bool(r[7]),
                        ktp_doc_id=str(r[8]) if r[8] is not None else None,
                        ktp_generated_at=str(r[9]) if r[9] is not None else None,
                        concentration_risk=bool(r[10]),
                        active_projects_count=int(r[11] or 0),
                        open_tasks_count=int(r[12] or 0),
                        is_handed_over_to_me=bool(r[13]),
                    )
                )
            return results

        return await run_in_threadpool(_exec)

    async def assign_handover(
        self,
        source_person_id: str,
        target_person_id: str,
        notes: str | None,
        user: User,
    ) -> AssignHandoverResponse:
        """
        Creates directed [:HANDED_OVER_TO] edge in FalkorDB from source person
        (and any locked KTP Document) to target successor.
        Enforces Admin or Manager authorization.
        """
        def _exec() -> AssignHandoverResponse:
            role_name = (user.role or "").strip().lower()
            clearance = (user.clearance_level or "Internal").capitalize()
            is_super = getattr(user, "is_superuser", False)
            is_admin = role_name in ("executive admin", "admin", "system_admin") or is_super or clearance == "Restricted"

            src_pid = _safe_str(source_person_id)
            tgt_pid = _safe_str(target_person_id)

            if src_pid == tgt_pid:
                raise ValueError("Source person and target successor cannot be the same individual.")

            # Validate authorization: Admin or Manager of source
            if not is_admin:
                req_pid = user.person_entity_id
                if not req_pid:
                    raise PermissionError("User account is not linked to a Person entity to authorize handover.")
                mgr_cypher = f"""
                MATCH path = (m:Person {{id: '{_safe_str(req_pid)}'}})-[:MANAGES*1..2]->(t:Person {{id: '{src_pid}'}})
                RETURN count(path)
                """
                mgr_res = self.client.query(mgr_cypher)
                if not mgr_res or not mgr_res[0] or mgr_res[0][0] == 0:
                    raise PermissionError("Only System Administrators or Managers of the individual may assign handovers.")

            # Verify target person exists
            tgt_check = self.client.query(f"MATCH (p:Person {{id: '{tgt_pid}'}}) RETURN p.id, coalesce(p.full_name, p.name)")
            if not tgt_check or not tgt_check[0]:
                raise ValueError(f"Target successor person '{target_person_id}' not found in Knowledge Graph.")

            now_iso = datetime.now(timezone.utc).isoformat()
            safe_notes = _safe_str(notes or "")
            assigner_label = _safe_str(user.full_name or user.email)

            # 1. Establish [:HANDED_OVER_TO] between persons in FalkorDB
            ho_cypher = f"""
            MATCH (s:Person {{id: '{src_pid}'}}), (t:Person {{id: '{tgt_pid}'}})
            MERGE (s)-[r:HANDED_OVER_TO]->(t)
            SET r.assigned_by = '{assigner_label}',
                r.assigned_at = '{now_iso}',
                r.status = 'active',
                r.notes = '{safe_notes}'
            RETURN s.id, t.id
            """
            self.client.query(ho_cypher)

            # 2. Also link any generated KTP Document to the target successor
            doc_link_cypher = f"""
            MATCH (d:Document)-[:DOCUMENTS]->(s:Person {{id: '{src_pid}'}}), (t:Person {{id: '{tgt_pid}'}})
            WHERE d.document_type = 'knowledge_transfer_package'
            MERGE (d)-[r:HANDED_OVER_TO]->(t)
            SET r.assigned_at = '{now_iso}',
                r.assigned_by = '{assigner_label}',
                r.status = 'active'
            """
            self.client.query(doc_link_cypher)

            return AssignHandoverResponse(
                success=True,
                message=f"Knowledge base for {source_person_id} successfully handed over to {target_person_id}.",
                source_person_id=source_person_id,
                target_person_id=target_person_id,
                assigned_at=now_iso,
            )

        return await run_in_threadpool(_exec)

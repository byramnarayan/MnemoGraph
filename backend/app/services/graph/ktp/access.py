from __future__ import annotations

import logging
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.models.user import User
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


class KTPAccessEvaluator:
    """
    Evaluates KTP_ACCESS_POLICY:
    - Admin bypass -> full graph
    - 2-hop manager -> Tier 1-4, <= Confidential
    - Senior Group Peer -> Tier 2-4, <= Internal
    - HR Specialist -> Tier 1, <= Confidential
    - Active Handover Assignee (Successor) -> Tier 2-4, <= Internal
    Returns: (is_allowed, reason, effective_role)
    """

    def __init__(self, client: FalkorDBClient):
        self.client = client

    async def evaluate_access(self, user: User, target_person_id: str) -> tuple[bool, str, str]:
        def _exec() -> tuple[bool, str, str]:
            role_name = (user.role or "").strip().lower()
            clearance = (user.clearance_level or "Internal").capitalize()

            # Rule 1: Admin
            is_super = getattr(user, "is_superuser", False)
            if role_name in ("executive admin", "admin", "system_admin") or is_super or clearance == "Restricted":
                return True, "Authorized via System Administrator privilege", "admin"

            # Resolve requestor's person entity id
            req_pid = user.person_entity_id
            if not req_pid:
                clean_email = _safe_str(user.email)
                email_res = self.client.query(
                    f"MATCH (p:Person) WHERE p.email = '{clean_email}' OR p.name = '{_safe_str(user.full_name)}' RETURN p.id LIMIT 1"
                )
                if email_res and email_res[0]:
                    req_pid = email_res[0][0]

            # Rule 2: HR Specialist
            dept = (user.department or "").lower()
            if "hr" in role_name or "hr" in dept or "human resources" in dept or "people" in dept:
                return True, "Authorized via HR Department role", "hr"

            if not req_pid:
                return False, "User account is not linked to an institutional Person entity in the Knowledge Graph", "none"

            # Rule 3: Direct or 2-hop Manager
            mgr_cypher = f"""
            MATCH path = (m:Person {{id: '{_safe_str(req_pid)}'}})-[:MANAGES*1..2]->(t:Person {{id: '{_safe_str(target_person_id)}'}})
            RETURN count(path)
            """
            mgr_res = self.client.query(mgr_cypher)
            mgr_count = mgr_res[0][0] if mgr_res and mgr_res[0] else 0
            if mgr_count > 0:
                return True, "Authorized as direct or 2-hop organizational manager", "manager"

            # Rule 4: Senior Peer in the Same Group
            title = (user.title or "").lower()
            is_senior = any(s in role_name or s in title for s in ["senior", "staff", "principal", "lead", "director", "vp", "executive", "head"])
            group_cypher = f"""
            MATCH (m:Person {{id: '{_safe_str(req_pid)}'}})-[:MEMBER_OF]->(g:Group)<-[:MEMBER_OF]-(t:Person {{id: '{_safe_str(target_person_id)}'}})
            RETURN g.name, m.role_level, m.role
            LIMIT 1
            """
            group_res = self.client.query(group_cypher)
            if group_res and group_res[0]:
                if is_senior:
                    return True, "Authorized as Senior Group Peer", "peer_senior"

            # Rule 5: Active Handover Assignment to Requestor (Successor)
            ho_cypher = f"""
            MATCH (t:Person {{id: '{_safe_str(target_person_id)}'}})-[r:HANDED_OVER_TO]->(m:Person {{id: '{_safe_str(req_pid)}'}})
            WHERE coalesce(r.status, 'active') = 'active'
            RETURN count(r)
            """
            ho_res = self.client.query(ho_cypher)
            if ho_res and ho_res[0] and ho_res[0][0] > 0:
                return True, "Authorized as assigned knowledge successor via active handover", "peer_senior"

            return False, "Access denied: Requestor does not manage target, share a group at a senior level, possess an active handover, or hold admin rights.", "none"

        return await run_in_threadpool(_exec)


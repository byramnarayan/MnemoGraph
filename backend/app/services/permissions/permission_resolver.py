from __future__ import annotations

import logging
from typing import List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Person, Team
from app.models.user import User
from app.services.permissions.access_policy import AccessGrant, AccessPolicyResult
from app.services.permissions.inherited_permission_resolver import InheritedPermissionResolver

logger = logging.getLogger(__name__)


class PermissionResolver:
    """
    Evaluates whether a user can access a specific entity (Document, Project, etc.)
    by combining direct user grants, team memberships, and inherited grants.
    """

    def __init__(self, inherited_resolver: Optional[InheritedPermissionResolver] = None):
        self.inherited_resolver = inherited_resolver or InheritedPermissionResolver()

    async def get_user_team_ids(self, user_id: str, db: AsyncSession) -> Set[str]:
        """Resolves all team IDs associated with a user or matching Person record."""
        team_ids: Set[str] = set()

        # Check Person record
        stmt = select(Person).where(Person.id == str(user_id))
        res = await db.execute(stmt)
        person = res.scalar_one_or_none()
        if person and person.team_id:
            team_ids.add(person.team_id)

        # Check User record email link to Person if user_id is integer-like
        if str(user_id).isdigit():
            user_stmt = select(User).where(User.id == int(user_id))
            u_res = await db.execute(user_stmt)
            user = u_res.scalar_one_or_none()
            if user and user.email:
                p_stmt = select(Person).where(Person.email == user.email)
                p_res = await db.execute(p_stmt)
                p_match = p_res.scalar_one_or_none()
                if p_match and p_match.team_id:
                    team_ids.add(p_match.team_id)

        return team_ids

    async def check_access(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        required_level: str = "READ",
        db: Optional[AsyncSession] = None,
    ) -> AccessPolicyResult:
        """
        Determines if user_id is authorized to access entity_id.
        """
        if not db:
            return AccessPolicyResult(allowed=False, reason="no_database_session")

        # Admin bypass if user is superadmin
        if str(user_id).isdigit():
            user_stmt = select(User).where(User.id == int(user_id))
            u_res = await db.execute(user_stmt)
            user = u_res.scalar_one_or_none()
            if user and getattr(user, "is_superuser", False):
                return AccessPolicyResult(
                    allowed=True,
                    reason="user_is_superuser",
                    effective_access_level="ADMIN",
                )

        # Resolve all grants on this entity (direct + inherited)
        grants = await self.inherited_resolver.resolve_inherited_grants(entity_type, entity_id, db)

        # Public access check
        for g in grants:
            if g.principal_type in ("Public", "Role") and g.principal_id in ("public", "all"):
                return AccessPolicyResult(
                    allowed=True,
                    reason="public_access_grant",
                    effective_access_level=g.access_level,
                    grants=grants,
                )

        # Direct user grant check
        for g in grants:
            if g.principal_type == "User" and g.principal_id == user_id:
                return AccessPolicyResult(
                    allowed=True,
                    reason="direct_user_grant_or_ownership",
                    effective_access_level=g.access_level,
                    grants=grants,
                )

        # Team grant check
        user_teams = await self.get_user_team_ids(user_id, db)
        for g in grants:
            if g.principal_type == "Team" and g.principal_id in user_teams:
                return AccessPolicyResult(
                    allowed=True,
                    reason=f"team_membership_grant ({g.principal_id})",
                    effective_access_level=g.access_level,
                    grants=grants,
                )

        # If no explicit restriction was placed and document has no owner/team restriction, allow READ
        if not grants:
            return AccessPolicyResult(
                allowed=True,
                reason="default_open_workspace_entity",
                effective_access_level="READ",
                grants=[],
            )

        return AccessPolicyResult(
            allowed=False,
            reason="access_denied_insufficient_grants",
            grants=grants,
        )

    # -------------------------------------------------------------
    # UKGOE Step 5.2: Absolute Security & RBAC Enforcement (INV-05)
    # -------------------------------------------------------------
    CLEARANCE_MAP = {
        "Public": 0,
        "Internal": 1,
        "Confidential": 2,
        "Restricted": 3,
    }

    @classmethod
    def get_clearance_rank(cls, clearance: str | int | None) -> int:
        if isinstance(clearance, int):
            return clearance
        return cls.CLEARANCE_MAP.get(clearance or "Internal", 1)

    @classmethod
    def is_entity_authorized(cls, classification: str | None, user_clearance: str | int = "Internal") -> bool:
        """
        Entity-level clearance check: omits node if node classification rank > user clearance rank.
        """
        user_rank = cls.get_clearance_rank(user_clearance)
        node_rank = cls.get_clearance_rank(classification)
        return node_rank <= user_rank

    is_node_authorized = is_entity_authorized

    @classmethod
    def is_path_authorized(cls, path_nodes: list[dict[str, Any]], user_clearance: str | int = "Internal") -> bool:
        """
        Path-level absolute boundary enforcement:
        If ANY node along the multi-hop traversal path exceeds user clearance,
        drop the entire path to prevent partial identity leakage.
        """
        user_rank = cls.get_clearance_rank(user_clearance)
        for node in path_nodes:
            node_classification = node.get("classification")
            node_rank = cls.get_clearance_rank(node_classification)
            if node_rank > user_rank:
                return False
        return True

    @classmethod
    async def log_access_attempt(
        cls,
        db: AsyncSession,
        user_id: str,
        entity_id: str,
        access_level: str,
        granted: bool,
        reason: str | None = None,
    ) -> None:
        """
        Audits entity access attempts into entity_access_log.
        """
        try:
            from app.models.validation import EntityAccessLogRecord
            rec = EntityAccessLogRecord(
                user_id=str(user_id),
                entity_id=str(entity_id),
                access_level=access_level,
                granted=granted,
                reason=reason,
            )
            db.add(rec)
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not log entity access attempt: {e}")

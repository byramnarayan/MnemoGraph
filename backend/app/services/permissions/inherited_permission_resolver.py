from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document, Project, Team
from app.models.sync_reconciliation_job import PermissionPolicy
from app.services.permissions.access_policy import AccessGrant

logger = logging.getLogger(__name__)


class InheritedPermissionResolver:
    """
    Resolves permissions inherited through hierarchical containers:
    Workspace -> Project -> Document
    Team -> User
    """

    async def resolve_inherited_grants(
        self,
        entity_type: str,
        entity_id: str,
        db: AsyncSession,
    ) -> List[AccessGrant]:
        grants: List[AccessGrant] = []

        if entity_type == "Document":
            stmt = select(Document).where(Document.id == entity_id)
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()
            if doc:
                # 1. Direct owner grant
                if doc.owner_user_id:
                    grants.append(
                        AccessGrant(
                            principal_type="User",
                            principal_id=doc.owner_user_id,
                            access_level="ADMIN",
                            scope="DIRECT",
                        )
                    )
                # 2. Direct team grant
                if doc.team_id:
                    grants.append(
                        AccessGrant(
                            principal_type="Team",
                            principal_id=doc.team_id,
                            access_level="READ",
                            scope="DIRECT",
                        )
                    )
                # 3. Inherit from Project
                if doc.project_id:
                    proj_stmt = select(Project).where(Project.id == doc.project_id)
                    p_res = await db.execute(proj_stmt)
                    proj = p_res.scalar_one_or_none()
                    if proj and proj.owner_team_id:
                        grants.append(
                            AccessGrant(
                                principal_type="Team",
                                principal_id=proj.owner_team_id,
                                access_level="READ",
                                scope="INHERITED",
                                inherited_from=f"Project:{proj.id}",
                            )
                        )

        elif entity_type == "Project":
            p_stmt = select(Project).where(Project.id == entity_id)
            p_res = await db.execute(p_stmt)
            proj = p_res.scalar_one_or_none()
            if proj and proj.owner_team_id:
                grants.append(
                    AccessGrant(
                        principal_type="Team",
                        principal_id=proj.owner_team_id,
                        access_level="ADMIN",
                        scope="DIRECT",
                    )
                )

        # 4. Check explicit permission policies stored in DB
        pol_stmt = select(PermissionPolicy).where(
            PermissionPolicy.entity_type == entity_type,
            PermissionPolicy.entity_id == entity_id,
        )
        pol_res = await db.execute(pol_stmt)
        policies = pol_res.scalars().all()
        for p in policies:
            grants.append(
                AccessGrant(
                    principal_type=p.principal_type,
                    principal_id=p.principal_id,
                    access_level=p.access_level,
                    scope=p.scope,
                    inherited_from=p.inherited_from,
                )
            )

        return grants


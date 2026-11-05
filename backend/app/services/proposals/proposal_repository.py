from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_proposal import ActionProposalDraft

logger = logging.getLogger(__name__)


class ActionProposalRepository:
    """
    CRUD repository for relational Action Proposal drafts in PostgreSQL.
    """

    async def save_draft(
        self,
        db: AsyncSession,
        draft: ActionProposalDraft,
    ) -> ActionProposalDraft:
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        return draft

    async def get_draft_by_id(
        self,
        db: AsyncSession,
        proposal_id: str,
    ) -> ActionProposalDraft | None:
        stmt = select(ActionProposalDraft).where(ActionProposalDraft.id == proposal_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_drafts(
        self,
        db: AsyncSession,
        created_by_email: str | None = None,
        limit: int = 50,
    ) -> list[ActionProposalDraft]:
        stmt = select(ActionProposalDraft)
        if created_by_email:
            stmt = stmt.where(ActionProposalDraft.created_by_email == created_by_email)
        stmt = stmt.order_by(ActionProposalDraft.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def update_draft(
        self,
        db: AsyncSession,
        proposal_id: str,
        title: str | None = None,
        proposed_action: str | None = None,
        implementation_steps: list[str] | None = None,
        priority: str | None = None,
        status: str | None = None,
    ) -> ActionProposalDraft | None:
        draft = await self.get_draft_by_id(db, proposal_id)
        if not draft:
            return None

        if title is not None:
            draft.title = title
        if proposed_action is not None:
            draft.proposed_action = proposed_action
        if implementation_steps is not None:
            draft.implementation_steps = implementation_steps
        if priority is not None:
            draft.priority = priority
        if status is not None:
            draft.status = status

        await db.commit()
        await db.refresh(draft)
        return draft


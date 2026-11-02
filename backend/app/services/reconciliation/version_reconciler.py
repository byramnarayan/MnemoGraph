from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_reconciliation_job import DocumentVersionState
from app.services.reconciliation.change_detector import ChangeDetector

logger = logging.getLogger(__name__)


class VersionReconciler:
    """
    Maintains document version states, tracking current hash, previous hash,
    and update timestamps.
    """

    def __init__(self, detector: Optional[ChangeDetector] = None):
        self.detector = detector or ChangeDetector()

    async def get_or_create_state(
        self,
        document_id: str,
        source_id: str,
        db: AsyncSession,
        workspace_id: Optional[str] = None,
    ) -> DocumentVersionState:
        stmt = select(DocumentVersionState).where(DocumentVersionState.document_id == document_id)
        res = await db.execute(stmt)
        state = res.scalar_one_or_none()
        if not state:
            state = DocumentVersionState(
                document_id=document_id,
                source_id=source_id,
                workspace_id=workspace_id,
                version_hash="",
                previous_hash=None,
                is_deleted=False,
            )
            db.add(state)
            await db.flush()
        return state

    async def update_version(
        self,
        state: DocumentVersionState,
        new_hash: str,
        db: AsyncSession,
    ) -> None:
        state.previous_hash = state.version_hash
        state.version_hash = new_hash
        state.last_synced_at = datetime.now(UTC)
        state.last_seen_at = datetime.now(UTC)
        state.is_deleted = False
        await db.flush()


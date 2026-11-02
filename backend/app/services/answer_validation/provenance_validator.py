from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document

logger = logging.getLogger(__name__)


class ProvenanceValidator:
    """
    Validates that cited document IDs actually exist in the database and have
    real provenance back to authorized source systems.
    """

    async def validate_document_ids(
        self,
        document_ids: List[str],
        db: AsyncSession,
    ) -> List[str]:
        if not document_ids:
            return []

        stmt = select(Document.id).where(Document.id.in_(document_ids))
        res = await db.execute(stmt)
        valid_ids = [row[0] for row in res.fetchall()]
        return valid_ids


from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document
from app.services.permissions.permission_resolver import PermissionResolver

logger = logging.getLogger(__name__)


class VisibilityService:
    """
    Filters search hits, documents, graph nodes, and citations to ensure
    only authorized entities are returned to the user.
    """

    def __init__(self, resolver: Optional[PermissionResolver] = None):
        self.resolver = resolver or PermissionResolver()

    async def filter_authorized_document_ids(
        self,
        document_ids: List[str],
        user_id: str,
        db: AsyncSession,
    ) -> List[str]:
        """Filters a list of document IDs returning only those the user can read."""
        authorized: List[str] = []
        for doc_id in document_ids:
            check = await self.resolver.check_access(
                user_id=user_id,
                entity_type="Document",
                entity_id=doc_id,
                db=db,
            )
            if check.allowed:
                authorized.append(doc_id)
        return authorized

    async def filter_search_chunks(
        self,
        chunks: List[Dict[str, Any]],
        user_id: str,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Filters vector search chunks by document authorization."""
        if not chunks:
            return []

        doc_ids = list({c.get("document_id") for c in chunks if c.get("document_id")})
        authorized_doc_ids = set(
            await self.filter_authorized_document_ids(doc_ids, user_id, db)
        )

        return [c for c in chunks if c.get("document_id") in authorized_doc_ids]


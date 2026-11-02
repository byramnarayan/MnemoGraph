from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document, DocumentMetadata, SourceEntity

logger = logging.getLogger(__name__)


class CitationService:
    """Derives precise citations, canonical source URLs, and storage keys for evidence items."""

    async def resolve_citations(
        self,
        db: AsyncSession,
        doc_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Maps document IDs (e.g. source_id or uuid) to canonical title, source_url, and storage_key."""
        results: dict[str, dict[str, Any]] = {}

        for raw_id in doc_ids:
            clean_id = raw_id.replace("doc:", "")

            stmt = select(Document).where(
                (Document.id == clean_id) | (Document.source_id == clean_id)
            )
            doc_res = await db.execute(stmt)
            doc = doc_res.scalars().first()

            if doc:
                # Query metadata for source URL
                meta_res = await db.execute(
                    select(DocumentMetadata).where(DocumentMetadata.storage_key == doc.storage_key)
                )
                meta = meta_res.scalars().first()

                results[raw_id] = {
                    "document_id": doc.id,
                    "source_id": doc.source_id,
                    "title": doc.title,
                    "source_url": meta.source_url if (meta and meta.source_url) else f"https://databricks.workspace/notebooks/{doc.source_id}",
                    "storage_key": doc.storage_key,
                }
            else:
                results[raw_id] = {
                    "document_id": clean_id,
                    "source_id": clean_id,
                    "title": clean_id,
                    "source_url": f"https://databricks.workspace/notebooks/{clean_id}",
                    "storage_key": "",
                }

        return results


from __future__ import annotations

import hashlib
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import DocumentMetadata, DocumentVersion
from app.services.storage.s3_store import S3ObjectStore


class DocumentStore:
    """Manages document storage in S3 and checksum tracking / versioning in PostgreSQL."""

    def __init__(self, s3_store: S3ObjectStore | None = None):
        self.s3 = s3_store or S3ObjectStore()

    async def save_document(
        self,
        db: AsyncSession,
        source_entity_id: str,
        storage_key: str,
        content: bytes,
        mime_type: str = "text/plain",
        source_url: str | None = None,
    ) -> tuple[DocumentMetadata, bool]:
        """Uploads document bytes to S3 and records version in DB. Returns (metadata, is_changed)."""
        checksum = hashlib.sha256(content).hexdigest()

        # Check existing metadata
        res = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.source_entity_id == source_entity_id)
        )
        meta = res.scalars().first()

        if meta and meta.checksum == checksum:
            return meta, False  # No change

        # Upload bytes to S3
        await self.s3.put_object(key=storage_key, data=content, content_type=mime_type)

        if not meta:
            meta = DocumentMetadata(
                source_entity_id=source_entity_id,
                storage_key=storage_key,
                bucket_name=self.s3.bucket,
                mime_type=mime_type,
                size_bytes=len(content),
                checksum=checksum,
                source_url=source_url,
            )
            db.add(meta)
            await db.flush()

            version = DocumentVersion(
                document_id=meta.id,
                version_number=1,
                storage_key=storage_key,
                checksum=checksum,
            )
            db.add(version)
        else:
            meta.storage_key = storage_key
            meta.checksum = checksum
            meta.size_bytes = len(content)

            # Query latest version count
            v_res = await db.execute(
                select(DocumentVersion).where(DocumentVersion.document_id == meta.id)
            )
            v_count = len(v_res.scalars().all())

            version = DocumentVersion(
                document_id=meta.id,
                version_number=v_count + 1,
                storage_key=storage_key,
                checksum=checksum,
            )
            db.add(version)

        await db.commit()
        await db.refresh(meta)
        return meta, True


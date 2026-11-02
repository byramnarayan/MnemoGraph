from __future__ import annotations

import logging
from typing import List, Optional
from starlette.concurrency import run_in_threadpool
from qdrant_client import models

from app.core.config import settings
from app.services.vector.indexer import VectorIndexer
from app.services.vector.qdrant_client import QdrantService

logger = logging.getLogger(__name__)


class StaleVectorCleanup:
    """
    Deletes or purges vector chunks in Qdrant when a document is updated,
    moved, or deleted.
    """

    def __init__(self, qdrant: Optional[QdrantService] = None):
        self.qdrant = qdrant or QdrantService()

    async def delete_document_vectors(self, document_id: str) -> int:
        """
        Deletes all vector points where payload document_id matches.
        """
        def _exec():
            client = self.qdrant.client
            collection_name = self.qdrant.collection_name

            # Check if collection exists
            try:
                collections = [c.name for c in client.get_collections().collections]
                if collection_name not in collections:
                    return 0
            except Exception:
                return 0

            try:
                # Count points first
                count_res = client.count(
                    collection_name=collection_name,
                    count_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    ),
                )
                pts_count = count_res.count

                if pts_count > 0:
                    client.delete(
                        collection_name=collection_name,
                        points_selector=models.FilterSelector(
                            filter=models.Filter(
                                must=[
                                    models.FieldCondition(
                                        key="document_id",
                                        match=models.MatchValue(value=document_id),
                                    )
                                ]
                            )
                        ),
                    )
                    logger.info(f"Purged {pts_count} vector chunks for document {document_id}")

                return pts_count
            except Exception as e:
                logger.warning(f"Could not purge vectors for document {document_id}: {e}")
                return 0

        return await run_in_threadpool(_exec)


class VectorReconciliationService:
    """
    Orchestrates vector indexing updates and stale cleanup.
    """

    def __init__(self, cleanup: Optional[StaleVectorCleanup] = None):
        self.cleanup = cleanup or StaleVectorCleanup()

    async def reconcile_document_vectors(self, document_id: str, is_deleted: bool = False) -> int:
        """Purges stale vector chunks before reindexing or on deletion."""
        return await self.cleanup.delete_document_vectors(document_id)

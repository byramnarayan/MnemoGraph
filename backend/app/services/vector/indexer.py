from __future__ import annotations

import logging
import uuid
from typing import Any
from starlette.concurrency import run_in_threadpool
from qdrant_client.http.models import PointStruct

from app.services.vector.embeddings import embed_query, embed_texts
from app.services.vector.qdrant_client import QdrantService

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Simple sliding window text chunker."""
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


class VectorIndexer:
    """Chunks text, computes dense embeddings, and stores indexed points in Qdrant."""

    def __init__(self, qdrant_service: QdrantService | None = None):
        self.qdrant = qdrant_service or QdrantService()

    async def index_document(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any],
        chunk_size: int = 400,
    ) -> int:
        """Chunks and indexes document text into Qdrant."""
        chunks = chunk_text(text, chunk_size=chunk_size)
        if not chunks:
            return 0

        def _index():
            vectors = embed_texts(chunks)
            points = []
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
                # Deterministic UUID for idempotent upserts
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{idx}"))
                payload = dict(metadata)
                payload["document_id"] = document_id
                payload["chunk_index"] = idx
                payload["text"] = chunk

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            self.qdrant.client.upsert(
                collection_name=self.qdrant.collection_name,
                points=points,
            )
            return len(points)

        return await run_in_threadpool(_index)

    async def search(self, query: str, limit: int = 10, filter_dict: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Semantic search over vector embeddings."""
        def _search():
            q_vector = embed_query(query)
            # Use query_points for latest Qdrant client compatibility
            res = self.qdrant.client.query_points(
                collection_name=self.qdrant.collection_name,
                query=q_vector,
                limit=limit,
                with_payload=True,
            )
            results = []
            for hit in res.points:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                })
            return results

        return await run_in_threadpool(_search)


from __future__ import annotations

import logging
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Manages Qdrant vector database connection and collections."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        vector_dim: int = 384,
    ):
        self.url = url or settings.qdrant_url
        self.api_key = (
            api_key
            or (settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None)
        )
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.vector_dim = vector_dim or settings.embedding_dimension

        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        self._ensure_collection()
        self._ensure_payload_indexes()

    def _ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            names = [c.name for c in collections]
            if self.collection_name not in names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_dim,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception as e:
            logger.warning(f"Qdrant collection init check warning: {e}")

    def _ensure_payload_indexes(self) -> None:
        """Ensure document_id and connector_id are indexed as keyword for fast payload filtering."""
        try:
            from qdrant_client.http.models import PayloadSchemaType
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="connector_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


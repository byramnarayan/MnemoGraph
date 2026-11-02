from __future__ import annotations

import logging
from fastembed import TextEmbedding
from app.core.config import settings

logger = logging.getLogger(__name__)

_global_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    global _global_model
    if _global_model is None:
        logger.info(f"Loading FastEmbed model: {settings.embedding_model}")
        _global_model = TextEmbedding(model_name=settings.embedding_model)
    return _global_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed list of strings into dense vectors."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def embed_query(query: str) -> list[float]:
    """Embed single query string."""
    vectors = embed_texts([query])
    return vectors[0] if vectors else []


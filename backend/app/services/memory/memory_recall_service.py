from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class MemoryRecallService:
    """
    Pre-retrieval context expansion using Graphiti temporal episodic memory:
    - Resolves pronouns and shorthand ("she", "that project", "the Chicago incident")
    - Extracts recently touched topics from past interactions
    - Enriches retrieval terms before hitting canonical FalkorDB and Qdrant
    """

    def __init__(self, graphiti: GraphitiClient | None = None):
        self.graphiti = graphiti or GraphitiClient()

    async def recall_context(
        self,
        db: AsyncSession,
        user_id: int,
        user_email: str,
        current_query: str,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "recent_entities": [],
            "recent_topics": [],
            "expanded_query": current_query,
            "has_memory_context": False,
        }

        try:
            # 1. Fetch recent entities from PostgreSQL memory_entities
            res = await db.execute(
                text("""
                    SELECT entity_type, entity_value, normalized_value, frequency_count
                    FROM memory_entities
                    WHERE user_id = :uid
                    ORDER BY last_seen_at DESC
                    LIMIT 6
                """),
                {"uid": user_id},
            )
            rows = res.fetchall()
            recent_entities = [
                {"type": r[0], "value": r[1], "normalized": r[2], "frequency": r[3]}
                for r in rows
            ]
            context["recent_entities"] = recent_entities

            # 2. Recall recent Graphiti temporal overlay nodes from FalkorDB
            graphiti_recalls = self.graphiti.recall_recent_entities(user_email=user_email, limit=4)
            context["recent_topics"] = [g["target_name"] for g in graphiti_recalls if g.get("target_name")]

            # 3. Context expansion for shorthand phrases
            lower_q = current_query.lower()
            shorthand_keywords = ["she", "he", "it", "that", "this", "the same", "they", "outage", "project", "for it"]
            recent_candidate = None
            if context["recent_topics"]:
                recent_candidate = context["recent_topics"][0]
            elif context["recent_entities"]:
                recent_candidate = context["recent_entities"][0]["value"]

            if any(k in lower_q for k in shorthand_keywords) and recent_candidate:
                context["has_memory_context"] = True
                context["expanded_query"] = f"{current_query} (context: {recent_candidate})"

            return context
        except Exception as e:
            logger.warning(f"Error during memory recall: {e}")
            return context

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


class GraphitiClient:
    """
    Manages Graphiti temporal episodic & semantic memory overlay on FalkorDB.
    Maintains clean separation:
    - Canonical Business Graph: Person, Team, Project, Document, Decision
    - Graphiti Memory Overlay: EpisodeMemory, EntityRecall, TopicRecall
    """

    def __init__(self, falkor_client: FalkorDBClient | None = None):
        self.falkor = falkor_client or FalkorDBClient()

    def add_episode_memory(
        self,
        episode_id: str,
        user_email: str,
        session_id: str,
        query: str,
        summary: str,
        referenced_entity_ids: list[str],
        timestamp_str: str,
    ) -> bool:
        """
        Creates an EpisodeMemory node and connects it to the user's graph persona
        and any business entities referenced in the answer.
        """
        try:
            clean_query = query.replace("'", "\\'").replace('"', '\\"')[:300]
            clean_summary = summary.replace("'", "\\'").replace('"', '\\"')[:500]

            # 1. Create EpisodeMemory node and link to Person
            cypher = f"""
            MATCH (p:Person {{email: '{user_email}'}})
            MERGE (e:EpisodeMemory {{id: '{episode_id}'}})
            ON CREATE SET e.session_id = '{session_id}',
                          e.query = '{clean_query}',
                          e.summary = '{clean_summary}',
                          e.created_at = '{timestamp_str}'
            MERGE (p)-[:RECALLED {{at: '{timestamp_str}'}}]->(e)
            """
            self.falkor.query(cypher)

            # 2. Attach EpisodeMemory to referenced canonical entities
            for ent_id in referenced_entity_ids:
                clean_ent = ent_id.replace("'", "\\'")
                link_cypher = f"""
                MATCH (e:EpisodeMemory {{id: '{episode_id}'}}), (target {{id: '{clean_ent}'}})
                MERGE (e)-[:TOUCHED]->(target)
                """
                try:
                    self.falkor.query(link_cypher)
                except Exception:
                    pass

            return True
        except Exception as e:
            logger.warning(f"Failed to record Graphiti episode memory in FalkorDB: {e}")
            return False

    def recall_recent_entities(self, user_email: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Recalls recent entities touched in the user's past episodes to resolve shorthand
        and expand context during pre-retrieval.
        """
        try:
            cypher = f"""
            MATCH (p:Person {{email: '{user_email}'}})-[r:RECALLED]->(e:EpisodeMemory)-[:TOUCHED]->(target)
            RETURN e.query, labels(target)[0], target.id, target.name, target.title
            ORDER BY e.created_at DESC
            LIMIT {limit}
            """
            rows = self.falkor.query(cypher)
            results = []
            for row in rows:
                results.append({
                    "prior_query": row[0],
                    "target_label": row[1],
                    "target_id": row[2],
                    "target_name": row[3] or row[4] or row[2],
                })
            return results
        except Exception as e:
            logger.warning(f"Failed to recall Graphiti entities for user {user_email}: {e}")
            return []


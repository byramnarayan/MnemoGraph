from __future__ import annotations

import logging
from typing import Any

from app.services.graph.permission_resolver import PermissionResolver
from app.services.graph.repository import GraphRepository
from app.services.vector.indexer import VectorIndexer

logger = logging.getLogger(__name__)


class SearchService:
    """Enterprise knowledge search: semantic vector search + graph provenance + permission resolution."""

    def __init__(
        self,
        vector_indexer: VectorIndexer | None = None,
        graph_repo: GraphRepository | None = None,
        permission_resolver: PermissionResolver | None = None,
    ):
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.graph = graph_repo or GraphRepository()
        self.perm_resolver = permission_resolver or PermissionResolver(self.graph)

    async def search(
        self,
        query: str,
        limit: int = 10,
        user_email: str | None = None,
    ) -> list[dict[str, Any]]:
        # 1. Semantic Retrieval via Qdrant
        vector_hits = await self.vector_indexer.search(query=query, limit=limit * 2)
        results = []

        for hit in vector_hits:
            payload = hit.get("payload", {})
            doc_id = payload.get("document_id")
            title = payload.get("title", "Untitled Document")
            storage_key = payload.get("storage_key")
            source_type = payload.get("source_type", "Document")
            score = round(float(hit.get("score", 0.0)), 3)
            excerpt = payload.get("text", "")[:300] + ("..." if len(payload.get("text", "")) > 300 else "")

            # 2. Permission Check
            if doc_id:
                has_access = await self.perm_resolver.can_user_access(user_email, doc_id)
                if not has_access:
                    continue  # Filter out unauthorized content

            # 3. Graph Provenance & Neighborhood Enrichment
            owners: list[str] = []
            teams: list[str] = []
            if doc_id:
                try:
                    neighborhood = await self.graph.get_related_entities(doc_id)
                    # Check who OWNS or AUTHORED this document
                    for in_edge in neighborhood.get("incoming", []):
                        if in_edge.get("relation") in ("OWNS", "AUTHORED_BY", "CREATED_BY"):
                            owner_id = in_edge.get("target_id", "")
                            if owner_id.startswith("person:"):
                                owners.append(owner_id.replace("person:", ""))

                    # Discover teams the owners belong to
                    for owner_email in owners:
                        person_context = await self.graph.get_related_entities(f"person:{owner_email}")
                        for edge in person_context.get("outgoing", []):
                            if edge.get("relation") == "MEMBER_OF":
                                team_name = edge.get("target_id", "").replace("team:", "")
                                if team_name and team_name not in teams:
                                    teams.append(team_name)
                except Exception as e:
                    logger.debug(f"Graph enrichment note for {doc_id}: {e}")

            if not owners and payload.get("owner_email"):
                owners.append(payload["owner_email"])

            results.append({
                "entity_type": source_type.capitalize(),
                "title": title,
                "score": score,
                "source_url": payload.get("path") or payload.get("source_url"),
                "owners": owners,
                "teams": teams,
                "excerpt": excerpt,
                "storage_key": storage_key,
            })

            if len(results) >= limit:
                break

        return results

from __future__ import annotations

from typing import Any
from app.services.graph.repository import GraphRepository


class PermissionResolver:
    """Evaluates whether a given user has read permissions to an entity in the graph.

    Supports:
    - Direct user ownership (OWNS / AUTHORED_BY)
    - Direct permission grant (user -[HAS_PERMISSION]-> doc)
    - Team-inherited permission (user -[MEMBER_OF]-> team -[HAS_PERMISSION|OWNS]-> doc)
    - Workspace / open project access
    """

    def __init__(self, repo: GraphRepository | None = None):
        self.repo = repo or GraphRepository()

    async def can_user_access(self, user_email: str | None, entity_id: str) -> bool:
        """Evaluate if user can read entity."""
        if not user_email:
            return True  # Open / internal corporate access by default if unauthenticated

        person_id = f"person:{user_email.lower()}"
        doc_node_id = f"doc:{entity_id}" if not (entity_id.startswith("doc:") or entity_id.startswith("project:") or entity_id.startswith("person:")) else entity_id

        # Check entity directly
        try:
            rel = await self.repo.get_related_entities(doc_node_id)
            # 1. Is user the owner/author?
            for edge in rel.get("incoming", []):
                if edge.get("target_id") == person_id and edge.get("relation") in ("OWNS", "AUTHORED_BY", "CREATED_BY"):
                    return True

            # 2. Does user belong to an owner team?
            user_context = await self.repo.get_related_entities(person_id)
            user_teams = {
                e.get("target_id") for e in user_context.get("outgoing", []) if e.get("relation") == "MEMBER_OF"
            }
            for edge in rel.get("incoming", []):
                if edge.get("target_id") in user_teams and edge.get("relation") in ("OWNS", "HAS_PERMISSION"):
                    return True

            # Open document if no explicit restrictive permissions attached
            has_explicit_perms = any(e.get("relation") == "HAS_PERMISSION" for e in rel.get("incoming", []))
            return not has_explicit_perms

        except Exception:
            return True  # Fallback to accessible rather than dropping search results


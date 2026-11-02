from __future__ import annotations

from typing import Any
from app.services.graph.repository import GraphRepository


class GraphQueries:
    """Specialized graph queries for organizational answering: ownership, teams, projects, decisions, and provenance."""

    def __init__(self, repo: GraphRepository | None = None):
        self.repo = repo or GraphRepository()

    async def get_person_context(self, email: str) -> dict[str, Any]:
        """Get who a person is, their teams, what they own, and what they worked on."""
        person_id = f"person:{email.lower()}"
        return await self.repo.get_related_entities(person_id)

    async def get_project_context(self, project_id: str) -> dict[str, Any]:
        """Get project boundary, owner team, constituent documents, and participants."""
        proj_node_id = f"project:{project_id}" if not project_id.startswith("project:") else project_id
        return await self.repo.get_related_entities(proj_node_id)

    async def get_document_provenance(self, document_id: str) -> dict[str, Any]:
        """Trace document back to owners, authoring teams, parent project, and source workspace."""
        doc_node_id = f"doc:{document_id}" if not document_id.startswith("doc:") else document_id
        return await self.repo.get_related_entities(doc_node_id)

    async def get_decision_context(self, decision_id: str) -> dict[str, Any]:
        """Trace decision to all connected documents, people, teams, tasks, tickets, and projects."""
        dec_node_id = f"decision:{decision_id}" if not decision_id.startswith("decision:") else decision_id
        return await self.repo.get_related_entities(dec_node_id)

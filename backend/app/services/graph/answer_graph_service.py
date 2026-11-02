from __future__ import annotations

import logging
from typing import Any

from app.services.graph.graph_queries import GraphQueries
from app.services.graph.repository import GraphRepository

logger = logging.getLogger(__name__)


class AnswerGraphService:
    """Specialized graph traversal service for extracting context, teams, owners, and relation paths."""

    def __init__(
        self,
        repo: GraphRepository | None = None,
        queries: GraphQueries | None = None,
    ):
        self.repo = repo or GraphRepository()
        self.queries = queries or GraphQueries(self.repo)

    async def resolve_person_by_document(self, document_id: str) -> list[str]:
        """Resolves authors / owners for a document."""
        doc_node = f"doc:{document_id}" if not document_id.startswith("doc:") else document_id
        neighborhood = await self.repo.get_related_entities(doc_node)
        people = []
        for edge in neighborhood.get("incoming", []):
            if edge.get("relation") in ("OWNS", "AUTHORED_BY", "CREATED_BY"):
                target = edge.get("target_id", "")
                if target.startswith("person:"):
                    people.append(target.replace("person:", ""))
        return people

    async def resolve_team_by_person(self, person_email: str) -> list[str]:
        """Resolves teams a person is a member of."""
        person_node = f"person:{person_email.lower()}" if not person_email.startswith("person:") else person_email
        context = await self.repo.get_related_entities(person_node)
        teams = []
        for edge in context.get("outgoing", []):
            if edge.get("relation") == "MEMBER_OF":
                target = edge.get("target_id", "")
                if target.startswith("team:"):
                    teams.append(target.replace("team:", ""))
        return teams

    async def resolve_project_by_document(self, document_id: str) -> list[str]:
        """Resolves projects that contain this document."""
        doc_node = f"doc:{document_id}" if not document_id.startswith("doc:") else document_id
        neighborhood = await self.repo.get_related_entities(doc_node)
        projects = []
        for edge in neighborhood.get("incoming", []):
            if edge.get("relation") == "CONTAINS":
                target = edge.get("target_id", "")
                if target.startswith("project:"):
                    projects.append(target.replace("project:", ""))
        return projects

    async def resolve_decisions_for_document(self, document_id: str) -> list[str]:
        """Resolves decisions derived from this document."""
        doc_node = f"doc:{document_id}" if not document_id.startswith("doc:") else document_id
        neighborhood = await self.repo.get_related_entities(doc_node)
        decisions = []
        for edge in neighborhood.get("incoming", []):
            if edge.get("relation") == "DERIVED_FROM":
                target = edge.get("target_id", "")
                if target.startswith("decision:"):
                    decisions.append(target.replace("decision:", ""))
        return decisions

    async def resolve_entity_context(self, document_id: str) -> dict[str, Any]:
        """Compiles complete graph provenance for a document node."""
        people = await self.resolve_person_by_document(document_id)
        teams: list[str] = []
        for p in people:
            t = await self.resolve_team_by_person(p)
            for team_name in t:
                if team_name not in teams:
                    teams.append(team_name)

        projects = await self.resolve_project_by_document(document_id)
        decisions = await self.resolve_decisions_for_document(document_id)

        # Assemble human-readable relation path
        paths: list[dict[str, str]] = []
        if people:
            paths.append({"from": "Document", "to": "Person", "relation": "AUTHORED_BY"})
        if teams:
            paths.append({"from": "Person", "to": "Team", "relation": "MEMBER_OF"})
        if projects:
            paths.append({"from": "Team", "to": "Project", "relation": "BELONGS_TO"})
        if decisions:
            paths.append({"from": "Decision", "to": "Document", "relation": "DERIVED_FROM"})

        return {
            "people": people,
            "teams": teams,
            "projects": projects,
            "decisions": decisions,
            "relation_path": paths,
        }


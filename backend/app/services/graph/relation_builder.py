from __future__ import annotations

import logging
from typing import Any

from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class RelationBuilder:
    """Manages deterministic creation of business entity nodes and cross-cutting edges in FalkorDB."""

    def __init__(self, repo: GraphRepository | None = None):
        self.repo = repo or GraphRepository()

    async def upsert_decision_node(
        self,
        decision_id: str,
        title: str,
        status: str = "accepted",
        description: str | None = None,
        workspace_id: str | None = None,
    ) -> str:
        node_id = f"decision:{decision_id}"
        await self.repo.upsert_node(
            label=NodeLabel.DECISION,
            entity_id=node_id,
            properties={
                "title": title,
                "status": status,
                "description": description or "",
                "workspace_id": workspace_id or "",
            },
        )
        return node_id

    async def link_decision_to_document(self, decision_id: str, document_id: str, relation: str = "DERIVED_FROM") -> None:
        dec_node = f"decision:{decision_id}" if not decision_id.startswith("decision:") else decision_id
        doc_node = f"doc:{document_id}" if not document_id.startswith("doc:") else document_id
        await self.repo.upsert_edge(from_id=dec_node, to_id=doc_node, relation=relation)

    async def link_decision_to_person(self, decision_id: str, person_id_or_email: str, relation: str = "CREATED_BY") -> None:
        dec_node = f"decision:{decision_id}" if not decision_id.startswith("decision:") else decision_id
        person_node = f"person:{person_id_or_email.lower()}" if not person_id_or_email.startswith("person:") else person_id_or_email
        await self.repo.upsert_edge(from_id=dec_node, to_id=person_node, relation=relation)

    async def link_decision_to_project(self, decision_id: str, project_id: str, relation: str = "RELATED_TO") -> None:
        dec_node = f"decision:{decision_id}" if not decision_id.startswith("decision:") else decision_id
        proj_node = f"project:{project_id.lower().replace(' ', '-')}" if not project_id.startswith("project:") else project_id
        await self.repo.upsert_edge(from_id=dec_node, to_id=proj_node, relation=relation)

    async def link_decision_to_team(self, decision_id: str, team_name_or_id: str, relation: str = "RELATED_TO") -> None:
        dec_node = f"decision:{decision_id}" if not decision_id.startswith("decision:") else decision_id
        team_node = f"team:{team_name_or_id.lower().replace(' ', '-')}" if not team_name_or_id.startswith("team:") else team_name_or_id
        await self.repo.upsert_edge(from_id=dec_node, to_id=team_node, relation=relation)

    async def link_generic(self, from_id: str, to_id: str, relation: str) -> None:
        await self.repo.upsert_edge(from_id=from_id, to_id=to_id, relation=relation)


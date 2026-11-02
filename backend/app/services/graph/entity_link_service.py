from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Person, Project, Team
from app.models.provenance import Decision
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class EntityLinkService:
    """
    Links extracted entities and mentions back to known entities in FalkorDB
    and PostgreSQL.
    """

    def __init__(self, repo: Optional[GraphRepository] = None):
        self.repo = repo or GraphRepository()

    async def link_document_to_project(
        self,
        document_id: str,
        project_id: str,
        mention_count: int = 1,
    ) -> bool:
        """Create REFERENCES relationship from Document to Project in Graph if both exist."""
        try:
            doc_node = await self.repo.get_entity(document_id)
            proj_node = await self.repo.get_entity(project_id)
            if doc_node and proj_node:
                await self.repo.upsert_edge(
                    from_id=document_id,
                    to_id=project_id,
                    relation=RelationType.REFERENCES,
                    properties={"mention_count": mention_count, "type": "project_reference"},
                )
                return True
        except Exception as e:
            logger.warning(f"Failed to link document {document_id} to project {project_id} in graph: {e}")
        return False

    async def link_document_to_decision(
        self,
        document_id: str,
        decision_id: str,
        mention_count: int = 1,
    ) -> bool:
        """Create REFERENCES relationship from Document to Decision in Graph if both exist."""
        try:
            doc_node = await self.repo.get_entity(document_id)
            dec_node = await self.repo.get_entity(decision_id)
            if doc_node and dec_node:
                await self.repo.upsert_edge(
                    from_id=document_id,
                    to_id=decision_id,
                    relation=RelationType.REFERENCES,
                    properties={"mention_count": mention_count, "type": "decision_reference"},
                )
                return True
        except Exception as e:
            logger.warning(f"Failed to link document {document_id} to decision {decision_id} in graph: {e}")
        return False

    async def link_document_to_person_mention(
        self,
        document_id: str,
        person_id: str,
    ) -> bool:
        """Create MENTIONS edge from Document to Person."""
        try:
            doc_node = await self.repo.get_entity(document_id)
            person_node = await self.repo.get_entity(person_id)
            if doc_node and person_node:
                await self.repo.upsert_edge(
                    from_id=document_id,
                    to_id=person_id,
                    relation=RelationType.MENTIONS,
                    properties={"type": "person_mention"},
                )
                return True
        except Exception as e:
            logger.warning(f"Failed to link document {document_id} to person {person_id}: {e}")
        return False

    async def link_document_to_team_mention(
        self,
        document_id: str,
        team_id: str,
    ) -> bool:
        """Create MENTIONS edge from Document to Team."""
        try:
            doc_node = await self.repo.get_entity(document_id)
            team_node = await self.repo.get_entity(team_id)
            if doc_node and team_node:
                await self.repo.upsert_edge(
                    from_id=document_id,
                    to_id=team_id,
                    relation=RelationType.MENTIONS,
                    properties={"type": "team_mention"},
                )
                return True
        except Exception as e:
            logger.warning(f"Failed to link document {document_id} to team {team_id}: {e}")
        return False


from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Person, Project, Team
from app.models.document_section import (
    DecisionMention,
    DocumentMention,
    DocumentSection,
    ExtractedEntity,
    ProjectMention,
)
from app.models.provenance import Decision
from app.services.graph.entity_link_service import EntityLinkService
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType

logger = logging.getLogger(__name__)


class DocumentEnrichmentGraphService:
    """
    Connects enrichment outputs (sections, extracted entities, project mentions, decision mentions)
    into the FalkorDB knowledge graph.
    """

    def __init__(
        self,
        repo: Optional[GraphRepository] = None,
        link_service: Optional[EntityLinkService] = None,
    ):
        self.repo = repo or GraphRepository()
        self.link_service = link_service or EntityLinkService(self.repo)

    async def sync_enrichment_to_graph(
        self,
        document_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Inspects stored enrichment records for a document and updates FalkorDB
        with REFERENCES and MENTIONS relationships.
        """
        stats = {
            "project_links_created": 0,
            "decision_links_created": 0,
            "person_links_created": 0,
            "team_links_created": 0,
        }

        # 1. Project Mentions
        proj_stmt = select(ProjectMention).where(ProjectMention.document_id == document_id)
        proj_res = await db.execute(proj_stmt)
        project_mentions = proj_res.scalars().all()

        for pm in project_mentions:
            linked = await self.link_service.link_document_to_project(
                document_id=document_id,
                project_id=pm.project_id,
                mention_count=pm.mention_count,
            )
            if linked:
                stats["project_links_created"] += 1

        # 2. Decision Mentions
        dec_stmt = select(DecisionMention).where(DecisionMention.document_id == document_id)
        dec_res = await db.execute(dec_stmt)
        decision_mentions = dec_res.scalars().all()

        for dm in decision_mentions:
            linked = await self.link_service.link_document_to_decision(
                document_id=document_id,
                decision_id=dm.decision_id,
                mention_count=dm.mention_count,
            )
            if linked:
                stats["decision_links_created"] += 1

        # 3. People mentions from ExtractedEntity
        people_stmt = select(ExtractedEntity).where(
            ExtractedEntity.document_id == document_id,
            ExtractedEntity.entity_type == "person",
        )
        people_res = await db.execute(people_stmt)
        people_entities = people_res.scalars().all()

        if people_entities:
            # Query known people in db
            all_people_res = await db.execute(select(Person.id, Person.full_name, Person.email))
            known_people = all_people_res.fetchall()

            for pe in people_entities:
                val = pe.normalized_value.lstrip("@").lower()
                for p_id, p_name, p_email in known_people:
                    if (p_name and val in p_name.lower()) or (p_email and val in p_email.lower()):
                        linked = await self.link_service.link_document_to_person_mention(document_id, p_id)
                        if linked:
                            stats["person_links_created"] += 1
                        break

        # 4. Team mentions from ExtractedEntity
        team_stmt = select(ExtractedEntity).where(
            ExtractedEntity.document_id == document_id,
            ExtractedEntity.entity_type == "team",
        )
        team_res = await db.execute(team_stmt)
        team_entities = team_res.scalars().all()

        if team_entities:
            all_teams_res = await db.execute(select(Team.id, Team.name))
            known_teams = all_teams_res.fetchall()

            for te in team_entities:
                val = te.normalized_value.lower()
                for t_id, t_name in known_teams:
                    if t_name and (val in t_name.lower() or t_name.lower() in val):
                        linked = await self.link_service.link_document_to_team_mention(document_id, t_id)
                        if linked:
                            stats["team_links_created"] += 1
                        break

        logger.info(f"Graph enrichment completed for document {document_id}: {stats}")
        return stats


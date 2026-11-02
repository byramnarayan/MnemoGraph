from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document, Person, Project, Team
from app.models.provenance import (
    Artifact,
    Decision,
    DecisionLink,
    Meeting,
    ProvenanceRecord,
    Task,
    Ticket,
)
from app.services.graph.relation_builder import RelationBuilder
from app.services.graph.repository import GraphRepository

logger = logging.getLogger(__name__)


class ProvenanceService:
    """Traces decisions back to source work, projects, people, teams, tasks, tickets, and artifacts."""

    def __init__(
        self,
        graph_repo: GraphRepository | None = None,
        relation_builder: RelationBuilder | None = None,
    ):
        self.graph = graph_repo or GraphRepository()
        self.builder = relation_builder or RelationBuilder(self.graph)

    async def get_decision_provenance(self, db: AsyncSession, decision_id: str) -> dict[str, Any]:
        """Build full explainable provenance chain for a decision."""
        # 1. Fetch from PostgreSQL
        d_res = await db.execute(select(Decision).where(Decision.id == decision_id))
        decision = d_res.scalars().first()
        if not decision:
            return {}

        dec_node_id = f"decision:{decision.id}"
        neighborhood = await self.graph.get_related_entities(dec_node_id)

        source_docs: list[dict[str, Any]] = []
        related_people: list[dict[str, Any]] = []
        related_teams: list[dict[str, Any]] = []
        related_projects: list[dict[str, Any]] = []
        related_tasks: list[dict[str, Any]] = []
        related_tickets: list[dict[str, Any]] = []
        related_meetings: list[dict[str, Any]] = []
        related_artifacts: list[dict[str, Any]] = []
        relation_paths: list[dict[str, str]] = []

        # 2. Graph Outgoing and Incoming links
        all_edges = neighborhood.get("outgoing", []) + neighborhood.get("incoming", [])
        for edge in all_edges:
            rel = edge.get("relation")
            target_id = edge.get("target_id", "")
            lbl = edge.get("target_label", "")

            relation_paths.append({
                "from": "Decision",
                "to": lbl or target_id.split(":")[0].capitalize(),
                "relation": rel,
            })

        # 3. Direct relational lookup in Postgres
        # Source document
        if decision.source_document_id:
            doc_res = await db.execute(
                select(Document).where(
                    (Document.id == decision.source_document_id) | (Document.source_id == decision.source_document_id)
                )
            )
            doc = doc_res.scalars().first()
            if doc:
                source_docs.append({
                    "id": doc.id,
                    "title": doc.title,
                    "source_id": doc.source_id,
                    "storage_key": doc.storage_key,
                })

        # Creator / owner
        if decision.created_by_user_id:
            p_res = await db.execute(
                select(Person).where(
                    (Person.id == decision.created_by_user_id) | (Person.email == decision.created_by_user_id.lower())
                )
            )
            person = p_res.scalars().first()
            if person:
                related_people.append({
                    "id": person.id,
                    "name": person.full_name,
                    "email": person.email,
                    "role": person.role,
                })

        # Project
        if decision.project_id:
            proj_res = await db.execute(
                select(Project).where(
                    (Project.id == decision.project_id) | (Project.name == decision.project_id)
                )
            )
            project = proj_res.scalars().first()
            if project:
                related_projects.append({
                    "id": project.id,
                    "name": project.name,
                })

        # Tasks linked
        task_res = await db.execute(select(Task).where(Task.related_decision_id == decision.id))
        for t in task_res.scalars().all():
            related_tasks.append({"id": t.id, "title": t.title, "status": t.status})

        # Tickets linked
        ticket_res = await db.execute(select(Ticket).where(Ticket.related_decision_id == decision.id))
        for tk in ticket_res.scalars().all():
            related_tickets.append({"id": tk.id, "title": tk.title, "status": tk.status})

        # Meetings linked
        m_res = await db.execute(select(Meeting).where(Meeting.related_decision_id == decision.id))
        for mt in m_res.scalars().all():
            related_meetings.append({"id": mt.id, "title": mt.title, "meeting_time": str(mt.meeting_time)})

        # Artifacts linked
        art_res = await db.execute(select(Artifact).where(Artifact.related_decision_id == decision.id))
        for a in art_res.scalars().all():
            related_artifacts.append({"id": a.id, "title": a.title, "type": a.artifact_type})

        # DecisionLinks table
        links_res = await db.execute(select(DecisionLink).where(DecisionLink.decision_id == decision.id))
        for l in links_res.scalars().all():
            relation_paths.append({
                "from": "Decision",
                "to": l.related_entity_type,
                "relation": l.relation_type,
            })

        return {
            "decision_id": decision.id,
            "decision_title": decision.title,
            "source_documents": source_docs,
            "related_people": related_people,
            "related_teams": related_teams,
            "related_projects": related_projects,
            "related_tasks": related_tasks,
            "related_tickets": related_tickets,
            "related_meetings": related_meetings,
            "related_artifacts": related_artifacts,
            "relation_paths": relation_paths,
        }


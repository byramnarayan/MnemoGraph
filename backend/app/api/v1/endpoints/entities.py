from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.models.connector import Department, Document, DocumentMetadata, Person, Project, Team
from app.models.provenance import Decision, ProjectMember
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.graph_queries import GraphQueries
from app.services.graph.repository import GraphRepository

router = APIRouter()
graph_repo = GraphRepository()
graph_queries = GraphQueries(graph_repo)
falkor_client = FalkorDBClient()


def is_privileged_role(role_name: str | None) -> bool:
    if not role_name:
        return False
    r = role_name.lower()
    return any(keyword in r for keyword in ["admin", "hr", "manager", "director", "vp", "executive", "lead"])


@router.get("/teams")
async def list_teams(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Team))
    teams = res.scalars().all()
    return [{"id": t.id, "name": t.name, "department_id": t.department_id, "created_at": t.created_at} for t in teams]


@router.get("/teams/{team_id}")
async def get_team_details(
    team_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    t_res = await db.execute(select(Team).where((Team.id == team_id) | (Team.name == team_id)))
    team = t_res.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members_res = await db.execute(select(Person).where(Person.team_id == team.id))
    members = members_res.scalars().all()

    proj_res = await db.execute(select(Project).where(Project.owner_team_id == team.id))
    projects = proj_res.scalars().all()

    doc_res = await db.execute(select(Document).where(Document.team_id == team.id))
    documents = doc_res.scalars().all()

    graph_context = await graph_queries.get_team_context(team.name.lower().replace(" ", "-"))

    return {
        "id": team.id,
        "name": team.name,
        "department_id": team.department_id,
        "members": [{"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role} for m in members],
        "projects": [{"id": p.id, "name": p.name} for p in projects],
        "documents": [{"id": d.id, "title": d.title, "source_id": d.source_id} for d in documents],
        "graph_context": graph_context,
    }


@router.get("/projects")
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Project))
    projects = res.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "workspace_id": p.workspace_id,
            "owner_team_id": p.owner_team_id,
            "created_at": p.created_at,
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project_details(
    project_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    pr_res = await db.execute(
        select(Project).where((Project.id == project_id) | (Project.name == project_id))
    )
    project = pr_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    graph_context = await graph_queries.get_project_context(project.name.lower().replace(" ", "-"))

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "workspace_id": project.workspace_id,
        "owner_team_id": project.owner_team_id,
        "graph_context": graph_context,
    }


@router.get("/documents")
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Document).limit(200))
    documents = res.scalars().all()
    return [{"id": d.id, "title": d.title, "source_system": d.source_system, "source_id": d.source_id, "project_id": d.project_id} for d in documents]


@router.get("/documents/{document_id}")
async def get_document_details(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    res = await db.execute(
        select(Document).where(
            (Document.id == document_id) |
            (Document.source_id == document_id) |
            (Document.storage_key.ilike(f"%{document_id}%"))
        )
    )
    doc = res.scalars().first()
    if not doc:
        meta_fallback = await db.execute(
            select(DocumentMetadata).where(
                (DocumentMetadata.id == document_id) |
                (DocumentMetadata.storage_key.ilike(f"%{document_id}%"))
            )
        )
        meta_row = meta_fallback.scalars().first()
        if meta_row:
            graph_context = await graph_queries.get_document_provenance(document_id)
            return {
                "id": document_id,
                "title": meta_row.storage_key.split("/")[-1] if meta_row.storage_key else document_id,
                "source_system": "Databricks",
                "source_id": document_id,
                "storage_key": meta_row.storage_key,
                "mime_type": meta_row.mime_type or "application/octet-stream",
                "created_at": meta_row.created_at,
                "updated_at": meta_row.updated_at,
                "size_bytes": meta_row.size_bytes or 0,
                "checksum": meta_row.checksum,
                "graph_provenance": graph_context,
            }
        raise HTTPException(status_code=404, detail="Document not found")

    meta_res = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.storage_key == doc.storage_key)
    )
    meta = meta_res.scalars().first()
    graph_context = await graph_queries.get_document_provenance(doc.source_id or doc.id)

    return {
        "id": doc.id,
        "title": doc.title,
        "source_system": doc.source_system,
        "source_id": doc.source_id,
        "storage_key": doc.storage_key,
        "mime_type": doc.mime_type,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "size_bytes": meta.size_bytes if meta else 0,
        "checksum": meta.checksum if meta else None,
        "graph_provenance": graph_context,
    }

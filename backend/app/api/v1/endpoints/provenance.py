from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.services.vector.provenance_enricher import ProvenanceEnricher

router = APIRouter()
enricher = ProvenanceEnricher()


@router.get("/projects/{project_id}/decisions")
async def get_project_decisions(
    project_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await enricher.get_decisions_for_entity(db=db, entity_type="project", entity_id=project_id)


@router.get("/documents/{document_id}/decisions")
async def get_document_decisions(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await enricher.get_decisions_for_entity(db=db, entity_type="document", entity_id=document_id)


@router.get("/people/{person_id}/decisions")
async def get_person_decisions(
    person_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await enricher.get_decisions_for_entity(db=db, entity_type="person", entity_id=person_id)


@router.get("/teams/{team_id}/decisions")
async def get_team_decisions(
    team_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await enricher.get_decisions_for_entity(db=db, entity_type="team", entity_id=team_id)


@router.get("/workspaces/{workspace_id}/decisions")
async def get_workspace_decisions(
    workspace_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    return await enricher.get_decisions_for_entity(db=db, entity_type="workspace", entity_id=workspace_id)


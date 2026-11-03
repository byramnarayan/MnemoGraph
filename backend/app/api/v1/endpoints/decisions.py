from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.models.connector import Document, Person, Project
from app.models.provenance import Decision
from app.schemas.decision import (
    DecisionCreateRequest,
    DecisionCreateResponse,
    DecisionDetailResponse,
    DecisionLinkCreateRequest,
    DecisionLinkResponse,
    DecisionProvenanceResponse,
)
from app.services.graph.decision_graph_service import DecisionGraphService
from app.services.graph.provenance_service import ProvenanceService

router = APIRouter()
decision_service = DecisionGraphService()
provenance_service = ProvenanceService()


@router.post("", response_model=DecisionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    req: DecisionCreateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Default created_by_user_id to current user email or id if omitted
    if not req.created_by_user_id:
        req.created_by_user_id = current_user.email

    decision = await decision_service.create_decision(db=db, req=req)
    return DecisionCreateResponse(
        id=decision.id,
        title=decision.title,
        status="created",
    )


@router.get("", response_model=list[DecisionDetailResponse])
async def list_decisions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Decision))
    decisions = res.scalars().all()
    out = []
    for d in decisions:
        out.append(
            DecisionDetailResponse(
                id=d.id,
                title=d.title,
                description=d.description,
                status=d.status,
                impact=d.impact,
                learnings=d.learnings,
                timeline=d.timeline,
                project_id=d.project_id,
                workspace_id=d.workspace_id,
                source_document_id=d.source_document_id,
                created_by_user_id=d.created_by_user_id,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )
    return out


@router.get("/{decision_id}", response_model=DecisionDetailResponse)
async def get_decision(
    decision_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = res.scalars().first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    prov = await provenance_service.get_decision_provenance(db=db, decision_id=decision.id)

    return DecisionDetailResponse(
        id=decision.id,
        title=decision.title,
        description=decision.description,
        status=decision.status,
        impact=decision.impact,
        learnings=decision.learnings,
        timeline=decision.timeline,
        project_id=decision.project_id,
        workspace_id=decision.workspace_id,
        source_document_id=decision.source_document_id,
        created_by_user_id=decision.created_by_user_id,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        related_project=prov.get("related_projects", [None])[0] if prov.get("related_projects") else None,
        source_document=prov.get("source_documents", [None])[0] if prov.get("source_documents") else None,
        created_by_person=prov.get("related_people", [None])[0] if prov.get("related_people") else None,
        related_teams=prov.get("related_teams", []),
        related_docs=prov.get("source_documents", []),
        related_tasks=prov.get("related_tasks", []),
        related_tickets=prov.get("related_tickets", []),
        related_meetings=prov.get("related_meetings", []),
        related_artifacts=prov.get("related_artifacts", []),
    )


@router.get("/{decision_id}/provenance", response_model=DecisionProvenanceResponse)
async def get_decision_provenance_chain(
    decision_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    prov = await provenance_service.get_decision_provenance(db=db, decision_id=decision_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Decision provenance not found")

    return DecisionProvenanceResponse(
        decision_id=prov["decision_id"],
        decision_title=prov["decision_title"],
        source_documents=prov.get("source_documents", []),
        related_people=prov.get("related_people", []),
        related_teams=prov.get("related_teams", []),
        related_projects=prov.get("related_projects", []),
        related_tasks=prov.get("related_tasks", []),
        related_tickets=prov.get("related_tickets", []),
        related_meetings=prov.get("related_meetings", []),
        related_artifacts=prov.get("related_artifacts", []),
        relation_paths=prov.get("relation_paths", []),
    )


@router.post("/{decision_id}/links", response_model=DecisionLinkResponse)
async def create_decision_link(
    decision_id: str,
    req: DecisionLinkCreateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = res.scalars().first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    ok = await decision_service.add_decision_link(
        db=db,
        decision_id=decision.id,
        related_entity_type=req.related_entity_type,
        related_entity_id=req.related_entity_id,
        relation_type=req.relation_type,
    )
    return DecisionLinkResponse(ok=ok, message="Link added successfully")


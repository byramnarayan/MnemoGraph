from __future__ import annotations

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.services.proposals.proposal_generator import ActionProposalGeneratorService
from app.services.proposals.proposal_repository import ActionProposalRepository

router = APIRouter()
proposal_generator = ActionProposalGeneratorService()
proposal_repo = ActionProposalRepository()


class CreateProposalRequest(BaseModel):
    scenario_data: dict[str, Any] = Field(..., description="Validated predictive scenario data")


class UpdateProposalRequest(BaseModel):
    title: str | None = None
    proposed_action: str | None = None
    implementation_steps: list[str] | None = None
    priority: str | None = None
    status: str | None = None


class ProposalResponse(BaseModel):
    id: str
    title: str
    scenario_id: str
    problem_statement: str
    affected_scope: str
    proposed_action: str
    implementation_steps: list[str]
    suggested_role: str | None
    priority: str
    status: str
    verification_criteria: str | None
    evidence_citations: list[dict[str, Any]]
    created_by_email: str
    created_at: str
    updated_at: str


def _serialize(d) -> ProposalResponse:
    return ProposalResponse(
        id=d.id,
        title=d.title,
        scenario_id=d.scenario_id,
        problem_statement=d.problem_statement,
        affected_scope=d.affected_scope,
        proposed_action=d.proposed_action,
        implementation_steps=d.implementation_steps or [],
        suggested_role=d.suggested_role,
        priority=d.priority,
        status=d.status,
        verification_criteria=d.verification_criteria,
        evidence_citations=d.evidence_citations or [],
        created_by_email=d.created_by_email,
        created_at=d.created_at.isoformat() if d.created_at else "",
        updated_at=d.updated_at.isoformat() if d.updated_at else "",
    )


@router.post("/generate-draft", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def generate_draft_proposal(
    req: CreateProposalRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generates an editable Action Proposal draft from validated scenario evidence and saves to PostgreSQL."""
    try:
        draft = await proposal_generator.generate_and_save_proposal(
            db=db,
            scenario_data=req.scenario_data,
            user_email=current_user.email,
        )
        return _serialize(draft)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate proposal draft: {str(e)}")


@router.get("", response_model=list[ProposalResponse])
async def list_proposals(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
):
    """Lists proposal drafts created by or accessible to current user."""
    drafts = await proposal_repo.list_drafts(db, limit=limit)
    return [_serialize(d) for d in drafts]


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieves single proposal draft."""
    draft = await proposal_repo.get_draft_by_id(db, proposal_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Proposal draft not found.")
    return _serialize(draft)


@router.put("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: str,
    req: UpdateProposalRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Updates an existing proposal draft before formal review."""
    draft = await proposal_repo.update_draft(
        db=db,
        proposal_id=proposal_id,
        title=req.title,
        proposed_action=req.proposed_action,
        implementation_steps=req.implementation_steps,
        priority=req.priority,
        status=req.status,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Proposal draft not found.")
    return _serialize(draft)


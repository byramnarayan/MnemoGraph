from __future__ import annotations

from typing import Annotated, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.services.graph.ontology_evolution_service import OntologyEvolutionService

router = APIRouter()
evolution_service = OntologyEvolutionService()


class RuleRegistrationRequest(BaseModel):
    rule_yaml: str


class CandidateRejectRequest(BaseModel):
    reason: Optional[str] = None


class ConstraintRelaxRequest(BaseModel):
    property_name: str
    new_constraint: str


@router.get("/candidates")
async def list_candidates(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """
    Lists pending, approved, or rejected candidate classes and relationships.
    """
    records = await evolution_service.list_candidates(db, status=status_filter)
    return [
        {
            "id": r.id,
            "candidate_type": r.candidate_type,
            "candidate_name": r.candidate_name,
            "frequency": r.frequency,
            "status": r.status,
            "source_document_ids": r.source_document_ids,
            "exemplar_entities": r.exemplar_entities,
            "first_seen": r.first_seen.isoformat() if r.first_seen else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in records
    ]


@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(
    candidate_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    candidate_type: str = Query("CLASS", description="'CLASS' or 'RELATION'"),
):
    """
    Approves candidate class or relationship, executing migration across
    PostgreSQL, FalkorDB, and Qdrant.
    """
    try:
        if candidate_type.upper() == "RELATION":
            result = await evolution_service.confirm_candidate_relation(candidate_id, db)
        else:
            result = await evolution_service.confirm_candidate_class(candidate_id, db)
        return result
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: str,
    req: CandidateRejectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """
    Rejects candidate class or relation and flags status as REJECTED.
    """
    try:
        result = await evolution_service.reject_candidate(candidate_id, db, reason=req.reason)
        return result
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/rules")
async def register_inference_rule(
    req: RuleRegistrationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """
    Registers a new dynamic YAML inference rule with cycle termination guarantees (max_depth <= 5)
    and executes a retrospective evaluation across FalkorDB.
    """
    try:
        result = await evolution_service.register_inference_rule(
            rule_yaml_str=req.rule_yaml,
            registered_by=current_user.email or "admin",
            db=db,
        )
        return result
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/violations")
async def list_constraint_violations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    resolved: bool = Query(False),
):
    """
    Lists property constraint violations and relaxation alerts.
    """
    violations = await evolution_service.list_violations(db, resolved=resolved)
    return [
        {
            "id": v.id,
            "entity_id": v.entity_id,
            "entity_class": v.entity_class,
            "property_name": v.property_name,
            "violation_value": v.violation_value,
            "expected_constraint": v.expected_constraint,
            "resolved": v.resolved,
            "occurred_at": v.occurred_at.isoformat() if v.occurred_at else None,
        }
        for v in violations
    ]


@router.post("/constraints/relax")
async def relax_constraint(
    req: ConstraintRelaxRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """
    Human-gated constraint relaxation: relaxes a property constraint and marks
    active violations as resolved.
    """
    result = await evolution_service.relax_constraint(
        property_name=req.property_name,
        new_constraint=req.new_constraint,
        db=db,
    )
    return result


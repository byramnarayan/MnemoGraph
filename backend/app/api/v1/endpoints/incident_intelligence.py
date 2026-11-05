from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics.decision_risk import (
    DecisionRiskService,
    DecisionRiskSummary,
)
from app.services.analytics.decision_deepdive import (
    DecisionDeepDiveService,
    DecisionDeepDiveNarrative,
)
from app.services.proposals.proposal_generator import ActionProposalGeneratorService

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateReportRequest(BaseModel):
    decision_id: str
    decision_title: str | None = None
    affected_scope: str | None = None
    incident_probability: float | None = 0.78
    executive_scenario: str | None = None
    recommended_action: dict[str, Any] | None = None
    evidence_citations: list[dict[str, Any]] | None = None
    user_email: str | None = "operations-lead@mnemograph.local"


@router.get(
    "/unlinked-decisions",
    response_model=list[DecisionRiskSummary],
    summary="List institutional decisions without linked incidents scored by risk",
)
async def list_unlinked_decisions(
    clearance: str = Query("Internal", description="User ABAC clearance level"),
) -> list[DecisionRiskSummary]:
    try:
        service = DecisionRiskService()
        return await service.list_unlinked_decisions_with_risk(user_clearance=clearance)
    except Exception as exc:
        logger.error(f"Failed to list unlinked decisions: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve unlinked decisions: {exc}",
        )


@router.get(
    "/decisions/{decision_id:path}/deep-dive",
    response_model=DecisionDeepDiveNarrative,
    summary="Generate multi-modal operational narrative deep-dive for a decision",
)
async def get_decision_deep_dive(
    decision_id: str,
    clearance: str = Query("Internal", description="User ABAC clearance level"),
) -> DecisionDeepDiveNarrative:
    try:
        service = DecisionDeepDiveService()
        return await service.get_decision_narrative_deepdive(
            decision_id=decision_id,
            user_clearance=clearance,
        )
    except Exception as exc:
        logger.error(f"Failed to generate deep dive for {decision_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate narrative deep dive: {exc}",
        )


@router.post(
    "/decisions/{decision_id:path}/generate-report",
    status_code=status.HTTP_201_CREATED,
    summary="Synthesize and save formal Action Proposal prevention report in PostgreSQL",
)
async def generate_action_proposal_report(
    decision_id: str,
    request: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        generator = ActionProposalGeneratorService()
        scenario_data = {
            "scenario_id": f"scen_{decision_id}",
            "possible_incident_type": "Interface Desynchronization & Packet Degradation",
            "affected_scope": request.affected_scope or "Core Telecom Infrastructure",
            "forecast_probability": request.incident_probability or 0.78,
            "forecast_horizon_days": 14,
            "recommended_action": request.recommended_action or {
                "action_title": f"Proactive Remediation Audit for {request.decision_title or decision_id}",
                "rationale": request.executive_scenario or "Proactive mitigation against unmitigated decision failure mode.",
                "suggested_role": "Lead Infrastructure Architect",
                "priority": "Critical" if (request.incident_probability or 0.5) >= 0.7 else "High",
                "implementation_steps": [
                    "1. Isolate and audit operational telemetry logs.",
                    "2. Verify transceiver power margin and buffer configuration.",
                    "3. Deploy verified corrective patch during scheduled maintenance window.",
                    "4. Confirm zero packet drop and stability for 24 hours.",
                ],
                "verification_criteria": "Zero packet drops observed and telemetry returned to baseline.",
            },
            "evidence_citation_ids": [c.get("id", "1") for c in (request.evidence_citations or [])],
        }
        draft = await generator.generate_and_save_proposal(
            db=db,
            scenario_data=scenario_data,
            user_email=request.user_email or "operations-lead@mnemograph.local",
        )
        return {
            "status": "DRAFT_CREATED",
            "proposal_id": draft.id,
            "title": draft.title,
            "affected_scope": draft.affected_scope,
            "problem_statement": draft.problem_statement,
            "proposed_action": draft.proposed_action,
            "implementation_steps": draft.implementation_steps,
            "suggested_role": draft.suggested_role,
            "priority": draft.priority,
            "verification_criteria": draft.verification_criteria,
            "evidence_citations": draft.evidence_citations,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
        }
    except Exception as exc:
        logger.error(f"Failed to generate proposal report for {decision_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate proposal report: {exc}",
        )


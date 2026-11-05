from __future__ import annotations

import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_proposal import ActionProposalDraft
from app.services.llm.groq_client import GroqClient
from app.services.proposals.proposal_repository import ActionProposalRepository

logger = logging.getLogger(__name__)


class ActionProposalGeneratorService:
    """
    Synthesizes formal, evidence-backed Action Proposal drafts from validated scenarios.
    """

    def __init__(
        self,
        repo: ActionProposalRepository | None = None,
        llm: GroqClient | None = None,
    ):
        self.repo = repo or ActionProposalRepository()
        self.llm = llm or GroqClient()

    async def generate_and_save_proposal(
        self,
        db: AsyncSession,
        scenario_data: dict[str, Any],
        user_email: str,
    ) -> ActionProposalDraft:
        sid = scenario_data.get("scenario_id", f"scen_{uuid.uuid4().hex[:8]}")
        rec = scenario_data.get("recommended_action", {})
        affected = scenario_data.get("affected_scope", "Core Network System")
        title = rec.get("action_title", f"Remediation Proposal for {affected}")
        rationale = rec.get("rationale", "Proactive mitigation against historical recurrence.")
        steps = rec.get("implementation_steps", [
            f"1. Isolate and audit operational logs for {affected}.",
            "2. Review configuration changes against baseline.",
            "3. Deploy tested corrective patch during off-peak window.",
            "4. Validate stability via synthetic health telemetry.",
        ])

        problem_stmt = (
            f"Predictive analysis identified potential failure mode '{scenario_data.get('possible_incident_type')}' "
            f"on {affected}. Forecast probability: {int(scenario_data.get('forecast_probability', 0.5) * 100)}% "
            f"over horizon of {scenario_data.get('forecast_horizon_days', 30)} days."
        )

        proposal_id = f"prop_{uuid.uuid4().hex[:10]}"

        # Assemble evidence citations from scenario
        citations: list[dict[str, Any]] = []
        for cit_id in scenario_data.get("evidence_citation_ids", []):
            citations.append({
                "citation_id": cit_id,
                "evidence_type": "FalkorDB Historical Precedent",
                "label": f"Historical Case Reference {cit_id}",
            })

        draft = ActionProposalDraft(
            id=proposal_id,
            title=title,
            scenario_id=sid,
            problem_statement=problem_stmt,
            affected_scope=affected,
            proposed_action=rationale,
            implementation_steps=steps,
            suggested_role=rec.get("suggested_role", "Lead Systems Engineer"),
            priority=rec.get("priority", "High"),
            status="DRAFT",
            verification_criteria=rec.get("verification_criteria", "Zero recurrence observed over 30-day window."),
            evidence_citations=citations,
            created_by_email=user_email,
        )

        return await self.repo.save_draft(db, draft)


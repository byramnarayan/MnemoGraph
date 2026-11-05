from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class DecisionDeepDiveNarrative(BaseModel):
    decision_id: str
    decision_title: str
    incident_probability: float
    risk_tier: str
    predicted_horizon: str
    executive_scenario: str
    narrative_timeline: str
    interconnected_context: str
    lessons_learned: str
    recommended_action: dict[str, Any]
    evidence_citations: list[dict[str, Any]] = Field(default_factory=list)


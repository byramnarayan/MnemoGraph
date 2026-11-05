from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class DecisionRiskSummary(BaseModel):
    decision_id: str
    decision_title: str
    decision_date: str | None = None
    decision_maker: str | None = None
    affected_systems: list[str] = Field(default_factory=list)
    incident_probability: float  # e.g. 0.78
    risk_tier: str  # "CRITICAL", "ELEVATED", "MODERATE", "LOW"
    predicted_horizon_days: str  # e.g. "14 to 30 days"
    lanobert_score: float = 0.0
    bottleneck_score: float = 0.0
    unimplemented_action_count: int = 0
    tasks_summary: list[dict[str, Any]] = Field(default_factory=list)


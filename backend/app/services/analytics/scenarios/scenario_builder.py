from __future__ import annotations

import hashlib
from typing import Any
from pydantic import BaseModel, Field

from app.services.analytics.forecasting.hazard_model import IncidentForecastResult
from app.services.analytics.scenarios.analogy_engine import HistoricalAnalogyEngine, HistoricalPrecedent


class RecommendedAction(BaseModel):
    action_title: str
    action_type: str  # "CORRECTIVE", "PREVENTATIVE", "INVESTIGATIVE"
    suggested_role: str = "Lead Systems Engineer"
    priority: str = "HIGH"  # "CRITICAL", "HIGH", "MEDIUM"
    rationale: str
    historical_precedent_action: str | None = None
    historical_outcome: str | None = None
    implementation_steps: list[str] = Field(default_factory=list)
    verification_criteria: str = ""


class PredictiveScenario(BaseModel):
    scenario_id: str
    scenario_title: str
    affected_scope: str
    possible_incident_type: str
    forecast_horizon_days: int = 30
    forecast_probability: float = 0.50
    predicted_interval: str = "14 to 30 days"
    uncertainty_level: str = "LOW"
    contributing_factors: list[str] = Field(default_factory=list)
    historical_precedent: HistoricalPrecedent | None = None
    recommended_action: RecommendedAction
    evidence_citation_ids: list[str] = Field(default_factory=list)


class ScenarioRecommendationEngine:
    """
    Constructs plausible incident scenarios and evidence-backed corrective actions.
    """

    def __init__(self, analogy_engine: HistoricalAnalogyEngine | None = None):
        self.analogy = analogy_engine or HistoricalAnalogyEngine()

    def build_scenarios_for_scope(
        self,
        entity_id: str,
        entity_scope: str,
        forecast: IncidentForecastResult,
    ) -> list[PredictiveScenario]:
        precedents = self.analogy.find_comparable_cases(entity_id, limit=2)
        top_precedent = precedents[0] if precedents else None

        prob_30d = 0.45
        for h in forecast.horizons:
            if h.horizon_days == 30:
                prob_30d = h.incident_probability

        # Deterministic scenario ID
        raw_sig = f"{entity_id}:{forecast.predicted_interval_days}:{prob_30d}"
        sid = f"scen_{hashlib.md5(raw_sig.encode()).hexdigest()[:10]}"

        # Craft recommended action from historical precedent
        eff = top_precedent.action_effectiveness if top_precedent else "EFFECTIVE"
        if eff == "INEFFECTIVE" or eff == "RECURRENCE":
            rec_title = f"Proactive Redundancy Switchover & Audit on {entity_scope}"
            rationale = f"Historical action '{top_precedent.historical_action_taken}' resulted in {eff}. Standard remediation must be elevated."
        else:
            rec_title = f"Synchronous Interface Integrity Calibration on {entity_scope}"
            rationale = f"Supported by effective prior precedent on {top_precedent.affected_system if top_precedent else 'network core'}."

        rec = RecommendedAction(
            action_title=rec_title,
            action_type="PREVENTATIVE" if prob_30d < 0.60 else "CORRECTIVE",
            suggested_role="Lead RF & Core Network Architect",
            priority="HIGH" if prob_30d >= 0.40 else "MEDIUM",
            rationale=rationale,
            historical_precedent_action=top_precedent.historical_action_taken if top_precedent else None,
            historical_outcome=top_precedent.action_effectiveness if top_precedent else None,
            implementation_steps=[
                f"1. Isolate target interface metrics on {entity_scope} ({entity_id}).",
                "2. Verify optical transceivers and packet error rate against baseline.",
                "3. Execute buffer realignment during scheduled low-traffic maintenance window.",
                "4. Conduct synthetic end-to-end latency health check.",
            ],
            verification_criteria="Packet loss dropped to 0.00% and LAnoBERT anomaly error_mean < 2.50 across 6-hour window.",
        )

        factors = [
            f"Forecast incident probability: {int(prob_30d * 100)}% over 30-day window",
            f"Log anomaly score (LAnoBERT): {forecast.lanobert_anomaly_score:.2f}",
            f"Structural graph centrality: {forecast.graph_centrality_score:.2f}",
        ]
        if forecast.rule_risk_signals_count > 0:
            factors.append(f"Flagged by {forecast.rule_risk_signals_count} UKGOE inference rules")

        scen = PredictiveScenario(
            scenario_id=sid,
            scenario_title=f"Potential Recurrent Service Degradation on {entity_scope}",
            affected_scope=f"{entity_scope} ({entity_id})",
            possible_incident_type="Core Optical Backhaul / Gateway Desynchronization",
            forecast_horizon_days=30,
            forecast_probability=prob_30d,
            predicted_interval=forecast.predicted_interval_days,
            uncertainty_level=forecast.uncertainty_level,
            contributing_factors=factors,
            historical_precedent=top_precedent,
            recommended_action=rec,
            evidence_citation_ids=[top_precedent.incident_id] if top_precedent else [],
        )

        return [scen]


from __future__ import annotations

import math
from typing import Any


class DecisionRiskCalculator:
    """
    Calibrates incident probability for an unmitigated operational decision
    by fusing LAnoBERT log anomaly scores, graph topology metrics, and task completion.
    """

    @staticmethod
    def calculate_incident_risk(
        lanobert_error_mean: float,
        bottleneck_score: float,
        tasks: list[dict[str, Any]],
        days_elapsed: int = 10,
    ) -> tuple[float, str, str]:
        """
        Returns (incident_probability, risk_tier, predicted_horizon).
        """
        # 1. Anomaly component: typical error_mean is ~1.5 to 5.0
        # Sigmoid scaling around 3.0
        anomaly_factor = 1.0 / (1.0 + math.exp(-1.2 * (lanobert_error_mean - 2.8)))

        # 2. Graph centrality / bottleneck component
        graph_factor = min(1.0, max(0.1, bottleneck_score * 1.5))

        # 3. Task status penalty: uncompleted or unassigned tasks amplify hazard
        total_tasks = len(tasks)
        if total_tasks == 0:
            task_penalty = 0.35  # No tasks assigned at all
        else:
            incomplete = sum(
                1 for t in tasks if str(t.get("status", "")).lower() not in ("completed", "done", "closed")
            )
            task_penalty = 0.40 * (incomplete / total_tasks)

        # 4. Temporal progression factor (older unmitigated decisions face higher failure window)
        time_factor = min(0.25, days_elapsed * 0.015)

        # 5. Composite raw hazard
        raw_prob = (0.45 * anomaly_factor) + (0.25 * graph_factor) + task_penalty + time_factor
        calibrated_prob = round(min(0.95, max(0.08, raw_prob)), 2)

        # 6. Risk Tier and Horizon
        if calibrated_prob >= 0.70:
            tier = "CRITICAL"
            horizon = "7 to 14 days"
        elif calibrated_prob >= 0.45:
            tier = "ELEVATED"
            horizon = "14 to 30 days"
        elif calibrated_prob >= 0.25:
            tier = "MODERATE"
            horizon = "30 to 60 days"
        else:
            tier = "LOW"
            horizon = "60 to 90 days"

        return calibrated_prob, tier, horizon


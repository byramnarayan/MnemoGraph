from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field

from app.services.ml.lanobert.scorer import LAnoBERTScorer


class LogAnomalyMetrics(BaseModel):
    entity_id: str
    entity_type: str
    window_hours: int = 24
    mean_anomaly_score: float = 0.0
    p95_anomaly_score: float = 0.0
    anomaly_trend: str = "STABLE"  # "INCREASING", "DECREASING", "STABLE"
    anomalous_line_count: int = 0
    total_lines_scored: int = 0
    model_checkpoint: str = "yukyung/LAnoBERT:hdfs"
    is_available: bool = True
    scored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LAnoBERTAggregator:
    """
    Aggregates line-level anomaly scores over temporal windows for operational graph entities.
    """

    def __init__(self, dataset: str = "hdfs"):
        self.scorer = LAnoBERTScorer(dataset=dataset)
        self.dataset = dataset

    def aggregate_log_stream(
        self,
        entity_id: str,
        entity_type: str,
        log_lines: list[str],
        window_hours: int = 24,
        anomaly_threshold: float = 4.5,
    ) -> LogAnomalyMetrics:
        """
        Computes aggregate window metrics over log lines.
        """
        if not log_lines:
            return LogAnomalyMetrics(
                entity_id=entity_id,
                entity_type=entity_type,
                window_hours=window_hours,
                is_available=False,
                model_checkpoint=f"yukyung/LAnoBERT:{self.dataset}",
            )

        scores = self.scorer.score_lines_batch(log_lines)
        valid_scores = [s for s in scores if s is not None]

        if not valid_scores:
            return LogAnomalyMetrics(
                entity_id=entity_id,
                entity_type=entity_type,
                window_hours=window_hours,
                is_available=False,
                model_checkpoint=f"yukyung/LAnoBERT:{self.dataset}",
            )

        valid_scores.sort()
        mean_score = sum(valid_scores) / len(valid_scores)
        idx_95 = int(len(valid_scores) * 0.95)
        p95_score = valid_scores[min(idx_95, len(valid_scores) - 1)]

        anomalous_count = sum(1 for s in valid_scores if s >= anomaly_threshold)

        # Simple trend computation comparing first half vs second half
        half = len(valid_scores) // 2
        trend = "STABLE"
        if half >= 3:
            first_half_mean = sum(valid_scores[:half]) / half
            second_half_mean = sum(valid_scores[half:]) / (len(valid_scores) - half)
            if second_half_mean > first_half_mean * 1.15:
                trend = "INCREASING"
            elif second_half_mean < first_half_mean * 0.85:
                trend = "DECREASING"

        return LogAnomalyMetrics(
            entity_id=entity_id,
            entity_type=entity_type,
            window_hours=window_hours,
            mean_anomaly_score=round(mean_score, 4),
            p95_anomaly_score=round(p95_score, 4),
            anomaly_trend=trend,
            anomalous_line_count=anomalous_count,
            total_lines_scored=len(valid_scores),
            model_checkpoint=f"yukyung/LAnoBERT:{self.dataset}",
            is_available=True,
        )

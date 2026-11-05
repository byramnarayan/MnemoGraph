from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.services.ml.lanobert.aggregator import LogAnomalyMetrics


class FusedTemporalFeatureVector(BaseModel):
    entity_id: str
    entity_scope: str  # System, Service, Site
    # LAnoBERT Log Anomaly Features
    lanobert_mean_error: float = 0.0
    lanobert_p95_error: float = 0.0
    lanobert_trend_slope: float = 0.0
    anomalous_line_ratio: float = 0.0
    has_valid_logs: bool = False
    # Graph Centrality & Community Features
    pagerank_score: float = 0.0
    betweenness_score: float = 0.0
    harmonic_centrality: float = 0.0
    community_id: int = 0
    wcc_component_id: int = 0
    connected_neighbor_count: int = 0
    # UKGOE Inference Signals
    causal_chain_depth: int = 0
    recurrence_risk_flag: bool = False
    blocking_dependency_risk: bool = False
    data_quality_grade: str = "A"
    # Historical Temporal Metrics
    days_since_last_incident: int = 90
    incident_count_preceding_90d: int = 0
    overdue_task_count: int = 0
    ineffective_action_history_count: int = 0


class TemporalFeatureFusionEngine:
    """
    Fuses multi-modal signals into a temporally-consistent feature vector without leakage.
    """

    @classmethod
    def fuse_features(
        cls,
        entity_id: str,
        entity_scope: str,
        log_metrics: LogAnomalyMetrics | None = None,
        graph_metrics: dict[str, Any] | None = None,
        inference_signals: dict[str, Any] | None = None,
        historical_stats: dict[str, Any] | None = None,
    ) -> FusedTemporalFeatureVector:
        gm = graph_metrics or {}
        inf = inference_signals or {}
        hist = historical_stats or {}

        # Log features
        mean_err = log_metrics.mean_anomaly_score if log_metrics and log_metrics.is_available else 0.0
        p95_err = log_metrics.p95_anomaly_score if log_metrics and log_metrics.is_available else 0.0
        tot_lines = log_metrics.total_lines_scored if log_metrics and log_metrics.is_available else 0
        anom_lines = log_metrics.anomalous_line_count if log_metrics and log_metrics.is_available else 0
        anom_ratio = (anom_lines / tot_lines) if tot_lines > 0 else 0.0
        trend_slope = 1.0 if log_metrics and log_metrics.anomaly_trend == "INCREASING" else (-1.0 if log_metrics and log_metrics.anomaly_trend == "DECREASING" else 0.0)

        return FusedTemporalFeatureVector(
            entity_id=entity_id,
            entity_scope=entity_scope,
            lanobert_mean_error=round(mean_err, 4),
            lanobert_p95_error=round(p95_err, 4),
            lanobert_trend_slope=trend_slope,
            anomalous_line_ratio=round(anom_ratio, 4),
            has_valid_logs=bool(log_metrics and log_metrics.is_available),
            pagerank_score=float(gm.get("pagerank", 0.0)),
            betweenness_score=float(gm.get("betweenness", 0.0)),
            harmonic_centrality=float(gm.get("harmonic_centrality", 0.0)),
            community_id=int(gm.get("community_id", 0)),
            wcc_component_id=int(gm.get("wcc_component_id", 0)),
            connected_neighbor_count=int(gm.get("neighbor_count", 0)),
            causal_chain_depth=int(inf.get("causal_depth", 0)),
            recurrence_risk_flag=bool(inf.get("recurrence_risk", False)),
            blocking_dependency_risk=bool(inf.get("blocking_dependency", False)),
            data_quality_grade=str(inf.get("data_quality_grade", "A")),
            days_since_last_incident=int(hist.get("days_since_last_incident", 90)),
            incident_count_preceding_90d=int(hist.get("incident_count_90d", 0)),
            overdue_task_count=int(hist.get("overdue_tasks", 0)),
            ineffective_action_history_count=int(hist.get("ineffective_actions", 0)),
        )


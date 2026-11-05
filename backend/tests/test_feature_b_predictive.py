import pytest
from app.services.ml.lanobert import LAnoBERTAggregator, LogAnomalyMetrics
from app.services.analytics.timeline import (
    ChronologicalTimelineSorter,
    DecisionFollowUpClassifier,
)
from app.services.analytics.forecasting import (
    TemporalFeatureFusionEngine,
    TemporalHazardForecastingModel,
)
from app.services.analytics.scenarios import (
    ScenarioRecommendationEngine,
)


def test_lanobert_aggregation_and_fallback():
    agg = LAnoBERTAggregator(dataset="hdfs")
    # Empty stream returns unavailable state gracefully
    metrics_empty = agg.aggregate_log_stream("system_test", "System", [])
    assert metrics_empty.is_available is False

    # Scored lines test
    lines = [
        "WARN [Interface] Jitter elevated at 0.42ms",
        "INFO [BGP] Keepalive acknowledged",
        "ERROR [Phy] Optical power degraded below -18dBm",
    ]
    metrics = agg.aggregate_log_stream("system_test", "System", lines)
    assert metrics.entity_id == "system_test"
    assert metrics.window_hours == 24


def test_chronological_timeline_sorter():
    raw_chains = [
        {
            "decision": {"id": "dec_1", "title": "Buffer Tuning", "decision_date": "2026-03-01 10:00:00"},
            "person": {"id": "p_1", "name": "Arjun Nair"},
            "task": {"id": "t_1", "title": "Apply config", "completion_date": "2026-03-02 12:00:00", "status": "COMPLETED"},
            "system": {"id": "sys_1", "name": "Bandra Kurla Telecom Tower"},
            "incident": {"id": "inc_1", "title": "Desynchronization", "start_datetime": "2026-03-10 08:00:00"},
        }
    ]

    events = ChronologicalTimelineSorter.assemble_events(raw_chains)
    assert len(events) == 3
    # Verify chronological ordering
    assert events[0].event_type == "DECISION_RECORDED"
    assert events[1].event_type == "ACTION_DEPLOYED"
    assert events[2].event_type == "INCIDENT_START"


def test_decision_followup_classification():
    raw_chains = [
        {
            "decision": {"id": "dec_old", "title": "Legacy Firmware Patch", "decision_date": "2026-01-01T00:00:00Z"},
            "task": {"id": "t_old", "status": "COMPLETED", "completion_date": "2026-01-02T00:00:00Z"},
            "system": {"name": "Connaught Place Hub"},
            "incident": {},
        },
        {
            "decision": {"id": "dec_recent", "title": "New Routing Protocol", "decision_date": "2026-11-01T00:00:00Z"},
            "task": {"id": "t_recent", "status": "ASSIGNED"},
            "system": {"name": "SITE-BLR-0012"},
            "incident": {},
        },
    ]

    summaries = DecisionFollowUpClassifier.evaluate_decisions(raw_chains)
    assert len(summaries) == 2
    # Verify newest first sorting
    assert summaries[0].decision_id == "dec_recent"
    assert summaries[0].follow_up_status == "ACTION_NOT_IMPLEMENTED"
    assert summaries[1].decision_id == "dec_old"
    assert summaries[1].follow_up_status == "NO_LINKED_INCIDENT_OBSERVED"


def test_temporal_hazard_forecasting():
    features = TemporalFeatureFusionEngine.fuse_features(
        entity_id="Bandra Kurla",
        entity_scope="System",
        graph_metrics={"pagerank": 0.45, "betweenness": 0.20},
        historical_stats={"days_since_last_incident": 30, "incident_count_90d": 1},
    )

    result = TemporalHazardForecastingModel.predict(features)
    assert result.forecast_status == "CALIBRATED_ESTIMATE"
    assert len(result.horizons) == 3
    # Check 7d < 30d < 90d cumulative hazard progression
    p_7 = result.horizons[0].incident_probability
    p_30 = result.horizons[1].incident_probability
    p_90 = result.horizons[2].incident_probability
    assert p_7 <= p_30 <= p_90


def test_scenario_recommendation_builder():
    features = TemporalFeatureFusionEngine.fuse_features(
        entity_id="SITE-BLR-0012",
        entity_scope="System",
        graph_metrics={"pagerank": 0.50},
    )
    forecast = TemporalHazardForecastingModel.predict(features)
    engine = ScenarioRecommendationEngine()
    scenarios = engine.build_scenarios_for_scope("SITE-BLR-0012", "System", forecast)

    assert len(scenarios) >= 1
    scen = scenarios[0]
    assert scen.scenario_id.startswith("scen_")
    assert scen.recommended_action.action_title is not None
    assert len(scen.recommended_action.implementation_steps) >= 3


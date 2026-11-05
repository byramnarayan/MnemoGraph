import pytest
from app.services.analytics.decision_risk import DecisionRiskService
from app.services.analytics.decision_deepdive import DecisionDeepDiveService


@pytest.mark.asyncio
async def test_decision_risk_service_unlinked_decisions():
    service = DecisionRiskService()
    results = await service.list_unlinked_decisions_with_risk()

    assert len(results) > 0
    for dec in results:
        assert dec.decision_id
        assert dec.decision_title
        assert 0.0 <= dec.incident_probability <= 1.0
        assert dec.risk_tier in ("CRITICAL", "ELEVATED", "MODERATE", "LOW")
        assert dec.predicted_horizon_days
        assert isinstance(dec.affected_systems, list)


@pytest.mark.asyncio
async def test_decision_deepdive_narrative_synthesis():
    service = DecisionDeepDiveService()
    deep_dive = await service.get_decision_narrative_deepdive("dec:buffer-tuning-bandra")

    assert deep_dive.decision_id == "dec:buffer-tuning-bandra"
    assert deep_dive.decision_title
    assert deep_dive.incident_probability >= 0.5
    assert len(deep_dive.executive_scenario) > 20
    assert len(deep_dive.narrative_timeline) > 20
    assert len(deep_dive.interconnected_context) > 20
    assert len(deep_dive.lessons_learned) > 20
    assert deep_dive.recommended_action.get("action_title")
    assert len(deep_dive.recommended_action.get("implementation_steps", [])) > 0
    assert len(deep_dive.evidence_citations) >= 2


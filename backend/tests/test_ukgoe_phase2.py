import pytest
import uuid
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.graph.inference_engine import UniversalInferenceEngine
from app.services.graph.schema import NodeLabel, RelationType


@pytest.fixture
def falkor():
    client = FalkorDBClient()
    return client


@pytest.fixture
def repo(falkor):
    return GraphRepository(client=falkor)


@pytest.fixture
def engine(falkor):
    return UniversalInferenceEngine(falkordb_client=falkor)


@pytest.mark.asyncio
async def test_node_upsert_diff_and_stub_resolution(repo, falkor):
    uid = f"test_person_{uuid.uuid4().hex[:8]}"

    # Step 1: Create Stub node
    stub_res = await repo.upsert_universal_node(
        label="Stub",
        entity_id=uid,
        properties={"name": "Unknown Eng", "status": "unresolved"},
    )
    assert stub_res["id"] == uid
    assert stub_res["is_stub"] is True

    # Verify in FalkorDB
    rows = falkor.query(f"MATCH (n {{id: '{uid}'}}) RETURN labels(n), n.name")
    assert len(rows) > 0
    labels, name = rows[0]
    assert "Stub" in labels

    # Step 2: Canonical upsert resolves stub
    resolved_res = await repo.upsert_universal_node(
        label="Person",
        entity_id=uid,
        properties={"full_name": "Dr. Priya Sharma", "email": "priya@telecom.internal"},
        source_doc_id="doc_postmortem_01",
    )
    assert resolved_res["id"] == uid

    # Verify labels evolved from Stub to Person and properties merged
    rows2 = falkor.query(f"MATCH (n {{id: '{uid}'}}) RETURN labels(n), n.full_name, n.property_history")
    labels2, full_name, history = rows2[0]
    assert "Person" in labels2
    assert "Stub" not in labels2
    assert full_name == "Dr. Priya Sharma"
    assert "diffs" in str(history) or "changed_at" in str(history)


@pytest.mark.asyncio
async def test_multi_cause_detection(repo, falkor):
    inc_target = f"inc_{uuid.uuid4().hex[:8]}"
    cause_a = f"inc_{uuid.uuid4().hex[:8]}"
    cause_b = f"inc_{uuid.uuid4().hex[:8]}"

    # Create 3 incident nodes
    await repo.upsert_universal_node("Incident", inc_target, {"title": "Target Outage", "severity": "P1"})
    await repo.upsert_universal_node("Incident", cause_a, {"title": "BGP Flap", "severity": "P2"})
    await repo.upsert_universal_node("Incident", cause_b, {"title": "Power Surge", "severity": "P2"})

    # Link first cause
    await repo.upsert_universal_edge(inc_target, cause_a, "CAUSED_BY", {"confidence": 0.95})
    rows1 = falkor.query(f"MATCH (n {{id: '{inc_target}'}}) RETURN labels(n)")
    assert "MULTI_CAUSE" not in rows1[0][0]

    # Link second cause -> should automatically tag target with :MULTI_CAUSE
    await repo.upsert_universal_edge(inc_target, cause_b, "CAUSED_BY", {"confidence": 0.92})
    rows2 = falkor.query(f"MATCH (n {{id: '{inc_target}'}}) RETURN labels(n)")
    assert "MULTI_CAUSE" in rows2[0][0]


@pytest.mark.asyncio
async def test_ir01_causal_chain_and_cycles(engine, repo, falkor):
    e1 = f"node_{uuid.uuid4().hex[:8]}"
    e2 = f"node_{uuid.uuid4().hex[:8]}"
    e3 = f"node_{uuid.uuid4().hex[:8]}"

    await repo.upsert_universal_node("Incident", e1, {"title": "Outage", "severity": "P1"})
    await repo.upsert_universal_node("Incident", e2, {"title": "Router Failure", "severity": "P2"})
    await repo.upsert_universal_node("Incident", e3, {"title": "Firmware Bug", "severity": "P3"})

    # e1 CAUSED_BY e2, e2 CAUSED_BY e3 (depth = 2)
    await repo.upsert_universal_edge(e1, e2, "CAUSED_BY")
    await repo.upsert_universal_edge(e2, e3, "CAUSED_BY")

    eval_res = await engine.evaluate_ir01_causal_chain(e1)
    assert eval_res["causal_depth"] == 2
    assert e3 in eval_res["root_causes"]
    assert eval_res["circular"] is False

    # Introduce cycle: e3 CAUSED_BY e1
    await repo.upsert_universal_edge(e3, e1, "CAUSED_BY")
    cycle_res = await engine.evaluate_ir01_causal_chain(e1)
    assert cycle_res["circular"] is True


@pytest.mark.asyncio
async def test_ir02_ir03_ir04_ir05_ir08(engine, repo, falkor):
    # IR-05: Temporal coherence
    valid, status = engine.evaluate_ir05_temporal_coherence({
        "start_datetime": "2024-03-01T10:00:00Z",
        "resolution_datetime": "2024-03-01T12:00:00Z"
    })
    assert valid is True
    assert status == "valid"

    invalid, bad_status = engine.evaluate_ir05_temporal_coherence({
        "start_datetime": "2024-03-01T12:00:00Z",
        "resolution_datetime": "2024-03-01T10:00:00Z"
    })
    assert invalid is False
    assert bad_status == "temporal_conflict"

    # IR-08: Completeness score
    score_a, grade_a = engine.evaluate_ir08_completeness("Project", {
        "name": "5G Core", "status": "active", "start_date": "2024-01-01"
    })
    assert score_a == 1.0
    assert grade_a == "A"

    score_d, grade_d = engine.evaluate_ir08_completeness("Project", {})
    assert score_d == 0.0
    assert grade_d == "D"

    # IR-02: Blocking dependency
    dep_id = f"task_{uuid.uuid4().hex[:8]}"
    blocked_id = f"task_{uuid.uuid4().hex[:8]}"
    await repo.upsert_universal_node("Task", dep_id, {"title": "DB Migration", "status": "failed"})
    await repo.upsert_universal_node("Task", blocked_id, {"title": "App Launch", "status": "open"})
    await repo.upsert_universal_edge(blocked_id, dep_id, "DEPENDS_ON")

    blocked_list = await engine.evaluate_ir02_blocking_dependency(dep_id, "failed")
    assert blocked_id in blocked_list

    # IR-03: Knowledge concentration
    person_id = f"lead_{uuid.uuid4().hex[:8]}"
    await repo.upsert_universal_node("Person", person_id, {"name": "Overworked Eng"})
    # Assign 6 critical tasks
    for i in range(6):
        t_id = f"crit_task_{uuid.uuid4().hex[:8]}"
        await repo.upsert_universal_node("Task", t_id, {"title": f"Crit Task {i}", "status": "open", "priority": "critical"})
        await repo.upsert_universal_edge(t_id, person_id, "ASSIGNED_TO")

    is_risk = await engine.evaluate_ir03_knowledge_concentration(person_id, threshold=5)
    assert is_risk is True


@pytest.mark.asyncio
async def test_ir09_ir10_cascade_and_merge(engine, repo, falkor):
    # IR-09: Cascade invalidation
    parent = f"rule9_p_{uuid.uuid4().hex[:8]}"
    child = f"rule9_c_{uuid.uuid4().hex[:8]}"
    await repo.upsert_universal_node("Project", parent, {"name": "Parent Project"})
    await repo.upsert_universal_node("Task", child, {"title": "Child Task"})
    await repo.upsert_universal_edge(parent, child, "DEPENDS_ON")

    invalidated = await engine.evaluate_ir09_cascade_invalidation(parent)
    assert child in invalidated

    # IR-10: Entity merge
    can_id = f"can_{uuid.uuid4().hex[:8]}"
    dup_id = f"dup_{uuid.uuid4().hex[:8]}"
    partner = f"part_{uuid.uuid4().hex[:8]}"

    await repo.upsert_universal_node("Person", can_id, {"name": "Alice Smith"})
    await repo.upsert_universal_node("Person", dup_id, {"name": "A. Smith"})
    await repo.upsert_universal_node("Project", partner, {"name": "Big Project"})
    await repo.upsert_universal_edge(dup_id, partner, "LEADS")

    merged = await engine.evaluate_ir10_entity_merge(can_id, dup_id)
    assert merged is True

    # Verify edge re-pointed to canonical Alice
    edge_rows = falkor.query(f"MATCH (p:Person {{id: '{can_id}'}})-[r:LEADS]->(pr:Project {{id: '{partner}'}}) RETURN count(r)")
    assert edge_rows[0][0] == 1

    # Verify dup is marked merged
    dup_rows = falkor.query(f"MATCH (d {{id: '{dup_id}'}}) RETURN d.status, d.merged_into")
    assert dup_rows[0][0] == "merged"
    assert dup_rows[0][1] == can_id


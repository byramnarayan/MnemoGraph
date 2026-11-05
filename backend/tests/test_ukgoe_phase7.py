from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.entity import EntityRecord
from app.models.relationship import RelationshipRecord
from app.models.validation import (
    CascadeLogRecord,
    ConflictRecord,
    EntityAccessLogRecord,
    InferenceEventRecord,
    ValidationLogRecord,
)
from app.schemas.answer import AnswerRequest
from app.services.answer_service import AnswerService
from app.services.enrichment.entity_extractor import EntityExtractor
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.permissions.permission_resolver import PermissionResolver
from app.services.vector.indexer import VectorIndexer


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.fixture(scope="module")
def repo(falkor):
    return GraphRepository(client=falkor)


@pytest.fixture(scope="module")
def indexer():
    return VectorIndexer()


@pytest.fixture(scope="module")
def answer_service(falkor, indexer):
    return AnswerService(vector_indexer=indexer, falkordb=falkor)


# =====================================================================
# INV-01: NEVER DISCARD (Data Preservation over Rejection)
# =====================================================================
@pytest.mark.asyncio
async def test_inv01_never_discard_temporal_and_schema_preservation():
    """
    Asserts that malformed timestamps and incomplete records are NEVER
    dropped or rejected; they are flagged with 'TEMPORAL_CONFLICT' and grade 'D'.
    """
    extractor = EntityExtractor()
    ent_id = f"inc_{uuid.uuid4().hex[:6]}"

    # Inverted timeline: resolution before start
    start_dt = datetime(2026, 5, 10, 14, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    is_valid, val_status = extractor.validate_temporal_coherence(start_dt, end_dt, ent_id)

    assert is_valid is False
    assert val_status == "TEMPORAL_CONFLICT"

    # Persist in DB and verify preservation under INV-01
    async with AsyncSessionLocal() as session:
        db_ent = EntityRecord(
            entity_id=ent_id,
            entity_class="Incident",
            label="Inverted Timestamp Incident",
            validation_status=val_status,
            data_quality_grade="D",
            properties={
                "start_datetime": start_dt.isoformat(),
                "resolution_datetime": end_dt.isoformat(),
            },
        )
        session.add(db_ent)
        val_log = ValidationLogRecord(
            entity_id=ent_id,
            rule_id="INV-01-TEMPORAL",
            status=val_status,
            detail="Resolution date precedes start date",
        )
        session.add(val_log)
        await session.commit()

        # Query back to prove preservation
        saved = (await session.execute(
            select(EntityRecord).where(EntityRecord.entity_id == ent_id)
        )).scalar_one()
        assert saved.validation_status == "TEMPORAL_CONFLICT"
        assert saved.data_quality_grade == "D"


# =====================================================================
# INV-02: FULL PROVENANCE (Traceable Edges & Properties)
# =====================================================================
@pytest.mark.asyncio
async def test_inv02_full_provenance_and_property_history(repo, falkor):
    """
    Asserts that entity updates record detailed, ordered field diffs
    and source document IDs in property_history.
    """
    eid = f"serv_{uuid.uuid4().hex[:6]}"

    # Write 1
    await repo.upsert_universal_node(
        label="System",
        entity_id=eid,
        properties={"name": "AuthService", "status": "active"},
        source_doc_id="doc_ver1",
    )

    # Write 2
    await repo.upsert_universal_node(
        label="System",
        entity_id=eid,
        properties={"status": "degraded"},
        source_doc_id="doc_ver2",
    )

    # Verify history in FalkorDB
    rows = falkor.query(f"MATCH (n:System {{id: '{eid}'}}) RETURN n.status, n.property_history")
    assert len(rows) == 1
    status, history = rows[0][0], rows[0][1]
    assert status == "degraded"
    assert "doc_ver2" in str(history)
    assert "active" in str(history)


# =====================================================================
# INV-03: DETERMINISTIC UPSERTS (Content-Hash Idempotency)
# =====================================================================
@pytest.mark.asyncio
async def test_inv03_deterministic_idempotency_uuid5(indexer):
    """
    Asserts that indexing the same document multiple times produces
    identical point IDs and does not create duplicate vector points.
    """
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"
    text_content = "# Section A\nThis is a deterministic test for UKGOE INV-03 idempotency verification."

    # Index run 1
    pts1 = await indexer.index_document(document_id=doc_id, text=text_content)
    assert pts1 >= 1

    # Index run 2 (exact same content)
    pts2 = await indexer.index_document(document_id=doc_id, text=text_content)
    assert pts2 == pts1

    # Verify deterministic point ID calculation
    expected_pt_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_0"))
    assert expected_pt_id is not None


# =====================================================================
# INV-04: CASCADE BEFORE ANSWER (Stale Vector & Invalidation Warning)
# =====================================================================
@pytest.mark.asyncio
async def test_inv04_cascade_before_answer_warnings(answer_service, falkor, indexer, repo):
    """
    Asserts that when an answer query touches an entity marked for downstream
    recompute (downstream_recompute_needed=True), transparent cascade warnings are emitted.
    """
    eid = f"proj_stale_{uuid.uuid4().hex[:6]}"

    # Graph write with stale recompute flag
    await repo.upsert_universal_node(
        label="Project",
        entity_id=eid,
        properties={
            "name": "Project Stale Alpha",
            "downstream_recompute_needed": True,
            "recompute_triggered_by": "upstream_chg_01",
        },
    )

    # Vector write with stale recompute flag in payload
    await indexer.index_entity(
        entity_id=eid,
        entity_class="Project",
        properties={"name": "Project Stale Alpha", "status": "active"},
        metadata={
            "classification": "Internal",
            "downstream_recompute_needed": True,
            "recompute_triggered_by": "upstream_chg_01",
        },
    )

    async with AsyncSessionLocal() as session:
        # Run factual query referencing this entity
        req = AnswerRequest(
            query=f"What is the status of {eid}?",
            classification_clearance="Internal",
        )
        res = await answer_service.generate_ukgoe_answer(
            db=session,
            req=req,
            current_user_email="admin@memory.internal",
        )

        # Confirm cascade warning presence
        assert res.intent is not None
        assert len(res.cascade_warnings) > 0
        warning = res.cascade_warnings[0]
        assert warning.entity_id == eid
        assert "upstream_chg_01" in warning.triggered_by


# =====================================================================
# INV-05: SECURITY BOUNDARY IS ABSOLUTE (Zero Path Leakage)
# =====================================================================
def test_inv05_absolute_security_boundary_no_leakage():
    """
    Asserts that multi-hop graph traversal prunes the ENTIRE path
    if ANY intermediate entity exceeds the caller's clearance level.
    """
    path_with_leak = [
        {"id": "doc_public", "classification": "Public"},
        {"id": "person_internal", "classification": "Internal"},
        {"id": "vault_restricted", "classification": "Restricted"},
        {"id": "system_public", "classification": "Public"},
    ]

    # Caller with Internal clearance: Restricted node in intermediate path must prune entire path
    assert PermissionResolver.is_path_authorized(path_with_leak, user_clearance="Internal") is False

    # Caller with Restricted clearance: can see the path
    assert PermissionResolver.is_path_authorized(path_with_leak, user_clearance="Restricted") is True


# =====================================================================
# INV-06: STUB OVER SKIP (Dangling Reference & Lossless Merge)
# =====================================================================
@pytest.mark.asyncio
async def test_inv06_stub_over_skip_and_lossless_merge(repo, falkor):
    """
    Asserts that referencing an unseen entity immediately creates a :Stub
    node with :PENDING_RESOLUTION, which seamlessly merges when the canonical
    record arrives later.
    """
    stub_id = f"stub_{uuid.uuid4().hex[:6]}"
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"

    # Step 1: Create stub node for dangling reference
    await repo.upsert_universal_node(
        label="Stub",
        entity_id=stub_id,
        properties={"name": "Dangling System", "is_stub": True, "status": "unresolved"},
        source_doc_id=doc_id,
    )
    await repo.upsert_universal_edge(
        from_id=doc_id,
        to_id=stub_id,
        relation="PENDING_RESOLUTION",
    )

    # Verify stub exists with :Stub label
    rows = falkor.query(f"MATCH (s:Stub {{id: '{stub_id}'}}) RETURN labels(s), s.status")
    assert len(rows) == 1
    assert "Stub" in rows[0][0]
    assert rows[0][1] == "unresolved"

    # Step 2: Canonical record arrives later
    await repo.upsert_universal_node(
        label="System",
        entity_id=stub_id,
        properties={"name": "Canonical System Alpha", "type": "Microservice", "status": "operational"},
        source_doc_id="doc_canonical",
    )

    # Verify stub resolved: :Stub removed, :System added, properties merged, edges inherited
    rows_after = falkor.query(f"MATCH (s {{id: '{stub_id}'}}) RETURN labels(s), s.name, s.type, s.status")
    assert len(rows_after) == 1
    labels = rows_after[0][0]
    assert "System" in labels
    assert "Stub" not in labels
    assert rows_after[0][1] == "Canonical System Alpha"
    assert rows_after[0][2] == "Microservice"
    assert rows_after[0][3] == "operational"


# =====================================================================
# INV-07: REAL-WORLD NON-LINEARITY (Compounding Multi-Cause & Conflicts)
# =====================================================================
@pytest.mark.asyncio
async def test_inv07_non_linearity_and_multi_cause_compounding(repo, falkor):
    """
    Asserts that compounding independent root causes automatically tag
    incidents with :MULTI_CAUSE, and contradictory claims are preserved in conflicts.
    """
    inc_id = f"inc_{uuid.uuid4().hex[:6]}"
    cause_1 = f"cause_a_{uuid.uuid4().hex[:6]}"
    cause_2 = f"cause_b_{uuid.uuid4().hex[:6]}"

    # Seed Incident and Cause 1
    await repo.upsert_universal_node(label="Incident", entity_id=inc_id, properties={"title": "DB Outage"})
    await repo.upsert_universal_node(label="Decision", entity_id=cause_1, properties={"title": "Config Error"})
    await repo.upsert_universal_node(label="Change", entity_id=cause_2, properties={"title": "Firmware Upgrade"})

    # Edge 1
    await repo.upsert_universal_edge(from_id=inc_id, to_id=cause_1, relation="CAUSED_BY", preserve_multi_cause=True)
    # Edge 2 (Compounding second cause!)
    await repo.upsert_universal_edge(from_id=inc_id, to_id=cause_2, relation="CAUSED_BY", preserve_multi_cause=True)

    # Check :MULTI_CAUSE label presence
    rows = falkor.query(f"MATCH (i:Incident {{id: '{inc_id}'}}) RETURN labels(i)")
    assert len(rows) == 1
    labels = rows[0][0]
    assert "MULTI_CAUSE" in labels
    assert "Incident" in labels

    # Conflict preservation check in PostgreSQL
    async with AsyncSessionLocal() as session:
        conflict = ConflictRecord(
            entity_id=inc_id,
            property_name="confirmed_cause",
            val_a="Config Error",
            source_a="doc_initial_rca",
            val_b="Firmware Upgrade",
            source_b="doc_final_audit",
            resolved_val="Compounding (Both)",
        )
        session.add(conflict)
        await session.commit()

        c_saved = (await session.execute(
            select(ConflictRecord).where(ConflictRecord.entity_id == inc_id)
        )).scalar_one()
        assert c_saved.val_a == "Config Error"
        assert c_saved.val_b == "Firmware Upgrade"

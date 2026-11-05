import pytest
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.ledger.relational_ledger_service import RelationalLedgerService


@pytest.fixture
def ledger():
    return RelationalLedgerService()


@pytest.mark.asyncio
async def test_atomic_entity_upsert_and_jsonb_append(ledger):
    ent_id = f"ent_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        # Step 1: Insert initial stub entity
        await ledger.upsert_entity_atomic(
            session=session,
            entity_id=ent_id,
            entity_class="Person",
            label="Alice Smith",
            properties={"title": "Engineer"},
            is_stub=True,
            completeness_score=0.6,
            validation_status="pending",
            data_quality_grade="C",
            source_document_id="doc_v1",
            diffs=[{"field": "status", "old": None, "new": "created"}],
        )
        await session.commit()

        # Verify initial insert
        row1 = (await session.execute(
            text("SELECT label, is_stub, completeness_score, source_document_ids, property_history FROM entities WHERE entity_id = :id"),
            {"id": ent_id}
        )).fetchone()
        assert row1 is not None
        assert row1[0] == "Alice Smith"
        assert row1[1] is True
        assert row1[2] == 0.6
        assert "doc_v1" in row1[3]

        # Step 2: Canonical update resolving stub and appending property history
        await ledger.upsert_entity_atomic(
            session=session,
            entity_id=ent_id,
            entity_class="Person",
            label="Dr. Alice Smith",
            properties={"title": "Principal Architect", "skills": ["Databases", "Distributed Systems"]},
            is_stub=False,
            completeness_score=1.0,
            validation_status="valid",
            data_quality_grade="A",
            source_document_id="doc_v2",
            diffs=[{"field": "title", "old": "Engineer", "new": "Principal Architect"}],
        )
        await session.commit()

        # Verify atomic update
        row2 = (await session.execute(
            text("SELECT label, is_stub, completeness_score, source_document_ids, property_history, data_quality_grade FROM entities WHERE entity_id = :id"),
            {"id": ent_id}
        )).fetchone()
        assert row2 is not None
        assert row2[0] == "Dr. Alice Smith"
        assert row2[1] is False  # stub resolved to false
        assert row2[2] == 1.0    # completeness updated
        assert row2[5] == "A"    # grade updated
        # Both doc_v1 and doc_v2 preserved in JSONB array
        assert "doc_v1" in row2[3]
        assert "doc_v2" in row2[3]
        # Property history contains both diff entries
        assert len(row2[4]) >= 2


@pytest.mark.asyncio
async def test_relationship_ledger_upsert(ledger):
    s_id = f"src_{uuid.uuid4().hex[:8]}"
    t_id = f"tgt_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        await ledger.upsert_relationship_atomic(
            session=session,
            source_id=s_id,
            target_id=t_id,
            relationship_type="DEPENDS_ON",
            confidence=0.98,
            context_text="Critical microservice dependency",
            source_document_id="doc_arch_01",
        )
        await session.commit()

        row = (await session.execute(
            text("SELECT source_id, target_id, relationship_type, confidence, context FROM relationships WHERE source_id = :sid AND target_id = :tid"),
            {"sid": s_id, "tid": t_id}
        )).fetchone()
        assert row is not None
        assert row[0] == s_id
        assert row[1] == t_id
        assert row[2] == "DEPENDS_ON"
        assert row[3] == 0.98
        assert "Critical microservice" in row[4]


@pytest.mark.asyncio
async def test_15_stage_topological_write(ledger):
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    person_mgr = f"person_{uuid.uuid4().hex[:8]}"
    person_emp = f"person_{uuid.uuid4().hex[:8]}"
    proj_id = f"proj_{uuid.uuid4().hex[:8]}"
    inc_id = f"inc_{uuid.uuid4().hex[:8]}"

    batch_entities = [
        # Stage 9: Operational (Project)
        {
            "entity_id": proj_id,
            "entity_class": "Project",
            "label": "Project Phoenix",
            "properties": {"status": "active"},
        },
        # Stage 4: Person (Employee with deferred manager_id)
        {
            "entity_id": person_emp,
            "entity_class": "Person",
            "label": "Bob Johnson",
            "properties": {"role": "SRE", "manager_id": person_mgr},
        },
        # Stage 1: Tier 0 (Organization)
        {
            "entity_id": org_id,
            "entity_class": "Organization",
            "label": "Aarohan Networks",
            "properties": {"hq": "Bangalore"},
        },
        # Stage 4: Person (Manager)
        {
            "entity_id": person_mgr,
            "entity_class": "Person",
            "label": "Carol Danvers",
            "properties": {"role": "Director"},
        },
        # Stage 8: Incident (with deferred project_id)
        {
            "entity_id": inc_id,
            "entity_class": "Incident",
            "label": "Core Gateway Outage",
            "properties": {"severity": "P1", "project_id": proj_id},
        },
    ]

    batch_relationships = [
        {"source_id": person_emp, "target_id": person_mgr, "relationship_type": "REPORTS_TO"},
        {"source_id": person_mgr, "target_id": proj_id, "relationship_type": "LEADS"},
        {"source_id": inc_id, "target_id": proj_id, "relationship_type": "AFFECTS"},
    ]

    async with AsyncSessionLocal() as session:
        result = await ledger.execute_15_stage_topological_write(
            session=session,
            entities=batch_entities,
            relationships=batch_relationships,
            source_document_id="doc_phoenix_01",
        )
        assert result["entities_upserted"] == 5
        assert result["relationships_written"] == 3

        # Verify Stage 13 resolved deferred manager_id in properties JSONB
        emp_row = (await session.execute(
            text("SELECT properties FROM entities WHERE entity_id = :id"),
            {"id": person_emp}
        )).fetchone()
        assert emp_row is not None
        assert emp_row[0].get("manager_id") == person_mgr

        # Verify Stage 13 resolved deferred project_id on Incident
        inc_row = (await session.execute(
            text("SELECT properties FROM entities WHERE entity_id = :id"),
            {"id": inc_id}
        )).fetchone()
        assert inc_row is not None
        assert inc_row[0].get("project_id") == proj_id


@pytest.mark.asyncio
async def test_user_authentication_preserved():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT count(*) FROM users WHERE id = 1 AND email = 'apex@gmail.com'"))
        count = res.scalar()
        assert count == 1, f"Expected admin user apex@gmail.com in users table, found {count}"

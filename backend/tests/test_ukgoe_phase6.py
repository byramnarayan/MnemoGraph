from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.entity import EntityRecord
from app.models.evolution import (
    ConstraintViolationRecord,
    InferenceRuleRecord,
    OntologyEvolutionRecord,
)
from app.models.relationship import RelationshipRecord
from app.models.validation import InferenceEventRecord
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.ontology_evolution_service import OntologyEvolutionService
from app.services.vector.qdrant_client import QdrantService


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.fixture(scope="module")
def qdrant():
    return QdrantService()


@pytest.fixture(scope="module")
def evolution_service(falkor, qdrant):
    return OntologyEvolutionService(graph_client=falkor, qdrant_service=qdrant)


@pytest.mark.asyncio
async def test_candidate_class_frequency_and_approval(evolution_service, falkor):
    async with AsyncSessionLocal() as session:
        # 1. Setup tables
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS ontology_evolution_log (
                id VARCHAR(36) PRIMARY KEY,
                candidate_type VARCHAR(50) NOT NULL,
                candidate_name VARCHAR(100) NOT NULL,
                source_document_ids JSONB DEFAULT '[]'::jsonb NOT NULL,
                exemplar_entities JSONB DEFAULT '[]'::jsonb NOT NULL,
                frequency INTEGER DEFAULT 1 NOT NULL,
                status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
                metadata_payload JSONB DEFAULT '{}'::jsonb NOT NULL,
                first_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS inference_rules (
                id VARCHAR(36) PRIMARY KEY,
                rule_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                trigger_entity VARCHAR(50) NOT NULL,
                rule_yaml TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                registered_by VARCHAR(100) DEFAULT 'system' NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS constraint_violations (
                id VARCHAR(36) PRIMARY KEY,
                entity_id VARCHAR(100) NOT NULL,
                entity_class VARCHAR(50) NOT NULL,
                property_name VARCHAR(100) NOT NULL,
                violation_value TEXT,
                expected_constraint TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE NOT NULL,
                occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """))
        await session.commit()

        test_class = f"SprintGoal_{uuid.uuid4().hex[:6]}"
        ent_id = f"ent_{uuid.uuid4().hex[:6]}"

        # Seed entity in PostgreSQL as Unclassified
        db_ent = EntityRecord(
            entity_id=ent_id,
            entity_class="Unclassified",
            label="Sprint Goal 42",
            properties={"candidate_class": test_class},
        )
        session.add(db_ent)
        await session.commit()

        # Seed in FalkorDB
        falkor.query(f"CREATE (n:Unclassified {{id: '{ent_id}', candidate_class: '{test_class}'}})")

        # Observation 1: Doc 1 -> frequency 1 (PENDING)
        is_cand = await evolution_service.evaluate_candidate_class(
            candidate_name=test_class,
            entity_id=ent_id,
            source_doc_id="doc_101",
            db=session,
        )
        assert is_cand is False

        # Observation 2: Doc 2 -> frequency 2 (PENDING)
        is_cand = await evolution_service.evaluate_candidate_class(
            candidate_name=test_class,
            entity_id=ent_id,
            source_doc_id="doc_102",
            db=session,
        )
        assert is_cand is False

        # Observation 3: Doc 3 -> frequency 3 (CANDIDATE triggered!)
        is_cand = await evolution_service.evaluate_candidate_class(
            candidate_name=test_class,
            entity_id=ent_id,
            source_doc_id="doc_103",
            db=session,
        )
        assert is_cand is True

        # Confirm candidate class approval migration
        res = await evolution_service.confirm_candidate_class(test_class, session)
        assert res["status"] == "APPROVED"
        assert res["candidate_name"] == test_class

        # Check PostgreSQL migration
        migrated_ent = (await session.execute(
            select(EntityRecord).where(EntityRecord.entity_id == ent_id)
        )).scalar_one()
        assert migrated_ent.entity_class == test_class

        # Check FalkorDB migration
        rows = falkor.query(f"MATCH (n:{test_class} {{id: '{ent_id}'}}) RETURN labels(n) AS lbls")
        assert len(rows) > 0
        assert test_class in rows[0][0]
        assert "Unclassified" not in rows[0][0]


@pytest.mark.asyncio
async def test_candidate_relation_frequency_and_approval(evolution_service, falkor):
    async with AsyncSessionLocal() as session:
        test_rel = f"CO_DEPLOYS_WITH_{uuid.uuid4().hex[:4]}".upper()
        s_id = f"sys_a_{uuid.uuid4().hex[:6]}"
        t_id = f"sys_b_{uuid.uuid4().hex[:6]}"

        # Seed edge in PostgreSQL
        rel_rec = RelationshipRecord(
            source_id=s_id,
            target_id=t_id,
            relationship_type="RELATED_TO",
            confidence=0.9,
            context=test_rel,
            source_document_id="doc_1",
        )
        session.add(rel_rec)
        await session.commit()

        # Seed edge in FalkorDB
        falkor.query(f"MERGE (a:System {{id: '{s_id}'}}) MERGE (b:System {{id: '{t_id}'}}) CREATE (a)-[:RELATED_TO {{candidate_relation_type: '{test_rel}'}}]->(b)")

        # Observations across 5 documents
        for i in range(1, 5):
            is_cand = await evolution_service.evaluate_candidate_relation(
                candidate_relation_type=test_rel,
                source_entity_id=s_id,
                target_entity_id=t_id,
                source_doc_id=f"doc_r{i}",
                db=session,
            )
            assert is_cand is False

        # 5th document elevates to CANDIDATE
        is_cand = await evolution_service.evaluate_candidate_relation(
            candidate_relation_type=test_rel,
            source_entity_id=s_id,
            target_entity_id=t_id,
            source_doc_id="doc_r5",
            db=session,
        )
        assert is_cand is True

        # Confirm approval migration
        res = await evolution_service.confirm_candidate_relation(test_rel, session)
        assert res["status"] == "APPROVED"

        # Check PostgreSQL
        updated_rel = (await session.execute(
            select(RelationshipRecord).where(
                RelationshipRecord.source_id == s_id,
                RelationshipRecord.target_id == t_id,
            )
        )).scalar_one()
        assert updated_rel.relationship_type == test_rel

        # Check FalkorDB
        rows = falkor.query(f"MATCH (a {{id: '{s_id}'}})-[r:{test_rel}]->(b {{id: '{t_id}'}}) RETURN count(r)")
        assert rows[0][0] == 1


@pytest.mark.asyncio
async def test_dynamic_yaml_inference_rule_safety_and_retrospective(evolution_service):
    async with AsyncSessionLocal() as session:
        # 1. Depth violation check: max_depth > 5 fails
        unsafe_depth_yaml = """
        rule_id: "IR-99"
        name: "DEEP_UNBOUNDED_SCAN"
        trigger_entity: "System"
        max_depth: 8
        conditions:
          - "EXISTS (system)<-[:OPERATES]-(group)"
        """
        with pytest.raises(ValueError, match="violates safety invariant bound of 5 hops"):
            await evolution_service.register_inference_rule(unsafe_depth_yaml, "analyst", session)

        # 2. Destructive keyword check: DROP or DELETE fails
        destructive_yaml = """
        rule_id: "IR-98"
        name: "MALICIOUS_DROP"
        trigger_entity: "System"
        max_depth: 2
        actions:
          - "DROP (system)"
        """
        with pytest.raises(ValueError, match="forbidden destructive operation"):
            await evolution_service.register_inference_rule(destructive_yaml, "analyst", session)

        # 3. Valid dynamic inference rule
        rule_id = f"IR_{uuid.uuid4().hex[:6]}"
        valid_yaml = f"""
        rule_id: "{rule_id}"
        name: "VENDOR_DEPENDENCY_RISK"
        trigger_entity: "System"
        max_depth: 3
        conditions:
          - "system.status IN ['under_maintenance', 'deprecated']"
        actions:
          - set: "dependent_projects.risk_flag = 'vendor_dependency_risk'"
        """
        res = await evolution_service.register_inference_rule(valid_yaml, "analyst", session)
        assert res["status"] == "ACTIVE"
        assert res["rule_id"] == rule_id

        # Verify stored in database
        rule_rec = (await session.execute(
            select(InferenceRuleRecord).where(InferenceRuleRecord.rule_id == rule_id)
        )).scalar_one()
        assert rule_rec.name == "VENDOR_DEPENDENCY_RISK"
        assert rule_rec.is_active is True


@pytest.mark.asyncio
async def test_property_constraint_violation_and_human_gated_relaxation(evolution_service):
    async with AsyncSessionLocal() as session:
        prop_name = f"desc_{uuid.uuid4().hex[:6]}"
        entity_class = "Project"

        # Record 19 violations -> should not trigger relaxation candidate yet
        for i in range(19):
            res = await evolution_service.record_constraint_violation(
                entity_id=f"proj_{i}",
                entity_class=entity_class,
                property_name=prop_name,
                violation_value="a" * 200,
                expected_constraint="max_length: 150",
                db=session,
            )
            assert res["relaxation_candidate"] is False

        # 20th violation -> triggers CONSTRAINT_RELAXATION_CANDIDATE
        res20 = await evolution_service.record_constraint_violation(
            entity_id="proj_20",
            entity_class=entity_class,
            property_name=prop_name,
            violation_value="a" * 200,
            expected_constraint="max_length: 150",
            db=session,
        )
        assert res20["relaxation_candidate"] is True

        # Relax constraint
        relax_res = await evolution_service.relax_constraint(
            property_name=prop_name,
            new_constraint="max_length: 250",
            db=session,
        )
        assert relax_res["status"] == "RELAXED"

        # Verify all existing records for this property are now resolved
        violations = await evolution_service.list_violations(session, resolved=False)
        unresolved_props = [v.property_name for v in violations]
        assert prop_name not in unresolved_props


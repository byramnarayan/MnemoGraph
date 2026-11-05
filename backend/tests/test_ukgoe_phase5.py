import pytest
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.schemas.answer import AnswerRequest
from app.services.answer_service import AnswerService, QueryClassifier
from app.services.permissions.permission_resolver import PermissionResolver
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.vector.indexer import VectorIndexer


@pytest.fixture
def falkor():
    return FalkorDBClient()


@pytest.fixture
def repo(falkor):
    return GraphRepository(client=falkor)


@pytest.fixture
def indexer():
    return VectorIndexer()


@pytest.fixture
def answer_service(falkor, indexer):
    return AnswerService(vector_indexer=indexer, falkordb=falkor)


def test_query_classifier_6_archetypes():
    assert QueryClassifier.classify_intent("What is the status of project Titan?") == "FACTUAL"
    assert QueryClassifier.classify_intent("Who led the team that built AuthGateway?") == "RELATIONAL"
    assert QueryClassifier.classify_intent("Which team depends on Network Operations?") == "RELATIONAL"
    assert QueryClassifier.classify_intent("Why did the VoNR deployment fail?") == "CAUSAL"
    assert QueryClassifier.classify_intent("What caused the authentication outage?") == "CAUSAL"
    assert QueryClassifier.classify_intent("Which engineering projects are at risk of delay?") == "PREDICTIVE"
    assert QueryClassifier.classify_intent("What is the recurrence risk for the BGP flap?") == "PREDICTIVE"
    assert QueryClassifier.classify_intent("Compare decision DEC-01 and DEC-02") == "COMPARATIVE"
    assert QueryClassifier.classify_intent("What is the difference between VoNR Phase 1 vs Phase 2?") == "COMPARATIVE"
    assert QueryClassifier.classify_intent("How many P1 incidents were misdiagnosed this quarter?") == "AGGREGATIVE"
    assert QueryClassifier.classify_intent("What is the total number of open tasks?") == "AGGREGATIVE"


@pytest.mark.asyncio
async def test_permission_resolver_inv05_and_audit_log():
    # 1. Single node clearance check (Step 5.2)
    assert PermissionResolver.is_entity_authorized("Public", user_clearance="Internal") is True
    assert PermissionResolver.is_entity_authorized("Internal", user_clearance="Internal") is True
    assert PermissionResolver.is_entity_authorized("Confidential", user_clearance="Internal") is False
    assert PermissionResolver.is_entity_authorized("Restricted", user_clearance="Confidential") is False

    # 2. Path-level pruning: ANY restricted node prunes entire path
    safe_path = [
        {"id": "doc_1", "classification": "Internal"},
        {"id": "person_1", "classification": "Internal"},
    ]
    assert PermissionResolver.is_path_authorized(safe_path, user_clearance="Internal") is True

    unsafe_path = [
        {"id": "doc_1", "classification": "Internal"},
        {"id": "secret_incident", "classification": "Confidential"},
        {"id": "person_2", "classification": "Internal"},
    ]
    # Pruned for Internal user
    assert PermissionResolver.is_path_authorized(unsafe_path, user_clearance="Internal") is False
    # Allowed for Confidential user
    assert PermissionResolver.is_path_authorized(unsafe_path, user_clearance="Confidential") is True

    # 3. Ensure table exists & access attempt audit logging into entity_access_log
    test_ent_id = f"ent_audit_{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_access_log (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                entity_id VARCHAR(100) NOT NULL,
                access_level VARCHAR(50) NOT NULL,
                granted BOOLEAN NOT NULL DEFAULT FALSE,
                reason VARCHAR(255),
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """))
        await session.commit()

        await PermissionResolver.log_access_attempt(
            db=session,
            user_id="user_test_99",
            entity_id=test_ent_id,
            access_level="READ",
            granted=False,
            reason="insufficient_clearance",
        )

        log_row = (await session.execute(
            text("SELECT user_id, entity_id, granted, reason FROM entity_access_log WHERE entity_id = :id"),
            {"id": test_ent_id}
        )).fetchone()
        assert log_row is not None
        assert log_row[0] == "user_test_99"
        assert log_row[2] is False
        assert log_row[3] == "insufficient_clearance"


@pytest.mark.asyncio
async def test_ukgoe_factual_answer_and_episodic_memory(answer_service, repo, indexer, falkor):
    unique_suffix = uuid.uuid4().hex[:6]
    proj_id = f"proj_titan_{unique_suffix}"
    proj_name = f"Project Titan Core {unique_suffix}"

    # Index project node in graph and vector
    await repo.upsert_universal_node("Project", proj_id, {
        "name": proj_name,
        "status": "active",
        "start_date": "2024-01-15",
    })

    await indexer.index_entity(
        entity_id=proj_id,
        entity_class="Project",
        properties={"name": proj_name, "status": "active", "start_date": "2024-01-15"},
        metadata={"classification": "Internal", "completeness_score": 1.0, "data_quality_grade": "A"},
    )

    req = AnswerRequest(
        query=f"What is the status of {proj_name}?",
        limit=3,
        classification_clearance="Internal",
    )

    async with AsyncSessionLocal() as session:
        response = await answer_service.generate_ukgoe_answer(
            db=session,
            req=req,
            current_user_email="admin@memory.internal",
        )

        assert response.intent == "FACTUAL"
        assert response.confidence > 0.0
        assert len(response.sources) > 0
        assert "Titan Core" in response.answer_text

        # Verify episodic memory written to PostgreSQL agent_episodes
        ep_row = (await session.execute(
            text("SELECT query_text, confidence_score FROM agent_episodes WHERE query_text = :q ORDER BY created_at DESC LIMIT 1"),
            {"q": req.query}
        )).fetchone()
        assert ep_row is not None
        assert ep_row[0] == req.query

        # Verify :EpisodeMemory node created in FalkorDB
        mem_rows = falkor.query(f"MATCH (m:EpisodeMemory)-[:TOUCHED]->(p {{id: '{proj_id}'}}) RETURN count(m)")
        assert mem_rows[0][0] >= 1


@pytest.mark.asyncio
async def test_causal_intent_and_graph_traversal(answer_service, repo, falkor):
    inc_id = f"inc_{uuid.uuid4().hex[:8]}"
    cause_id = f"cause_{uuid.uuid4().hex[:8]}"

    await repo.upsert_universal_node("Incident", inc_id, {"title": "VoNR Outage", "severity": "P1"})
    await repo.upsert_universal_node("Incident", cause_id, {"title": "Diameter Storm", "severity": "P2"})
    await repo.upsert_universal_edge(inc_id, cause_id, "CAUSED_BY")

    req = AnswerRequest(
        query="Why did the VoNR Outage fail?",
        limit=3,
    )

    async with AsyncSessionLocal() as session:
        response = await answer_service.generate_ukgoe_answer(
            db=session,
            req=req,
        )

        assert response.intent == "CAUSAL"
        assert response.graph_query_used is not None
        assert "CAUSED_BY" in response.graph_query_used
        assert len(response.inference_insights) > 0
        assert response.inference_insights[0].rule_id == "IR-01"

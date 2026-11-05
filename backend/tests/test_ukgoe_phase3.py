import pytest
import uuid
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.vector.indexer import StructureAwareChunker, VectorIndexer
from app.services.vector.qdrant_client import QdrantService
from app.services.vector.stale_vector_cleanup import CascadeReindexingService


@pytest.fixture
def falkor():
    return FalkorDBClient()


@pytest.fixture
def repo(falkor):
    return GraphRepository(client=falkor)


@pytest.fixture
def qdrant():
    return QdrantService()


@pytest.fixture
def indexer(qdrant):
    return VectorIndexer(qdrant_service=qdrant)


@pytest.fixture
def cascade_service(qdrant, falkor, indexer):
    return CascadeReindexingService(qdrant=qdrant, falkordb=falkor, indexer=indexer)


def test_structure_aware_chunker_render_entity():
    # Person rendering
    person_props = {
        "id": "person:priya",
        "full_name": "Dr. Priya Sharma",
        "role": "Lead Architect",
        "department": "Platform Engineering",
        "email": "priya@telecom.internal",
        "skills": ["Distributed Systems", "Cypher", "Kafka"],
        "employment_status": "active",
        "start_date": "2021-04-15",
    }
    neighbors = [
        {"id": "project:titan", "relation": "LEADS", "label": "Project"},
        {"id": "person:vikram", "relation": "REPORTS_TO", "label": "Person"},
    ]
    rendered_person = StructureAwareChunker.render_entity("Person", person_props, neighbors)
    assert "Dr. Priya Sharma" in rendered_person
    assert "Lead Architect" in rendered_person
    assert "Distributed Systems, Cypher, Kafka" in rendered_person
    assert "LEADS Project (project:titan)" in rendered_person

    # Incident rendering
    inc_props = {
        "id": "incident:inc-1024",
        "title": "Core Outage",
        "severity": "P1",
        "start_datetime": "2024-03-12 04:15 UTC",
        "resolution_datetime": "2024-03-12 06:45 UTC",
        "initial_suspected_cause": "Database Timeout",
        "confirmed_cause": "Diameter Signaling Storm",
        "is_mis_diagnosed": True,
        "description": "Critical gateway outage affecting authentication.",
    }
    rendered_inc = StructureAwareChunker.render_entity("Incident", inc_props)
    assert "Core Outage" in rendered_inc
    assert "Severity: P1" in rendered_inc
    assert "Confirmed root cause: Diameter Signaling Storm" in rendered_inc
    assert "Misdiagnosis occurred: true" in rendered_inc


def test_structure_aware_chunker_sections_and_breadcrumbs():
    doc_text = """# Architecture Overview
This section outlines the general principles of the universal ontology engine and distributed storage architecture. It must have enough words to be indexed properly without getting discarded by the min token filter threshold.

## Storage Layer
The database layer combines PostgreSQL for canonical transaction storage, FalkorDB for real-time graph traversals, and Qdrant for dense vector similarity search across multi-modal assets.

### Incident Remediation
All incidents are automatically tracked with root causes and corrective action items to prevent future occurrences.
"""
    chunks = StructureAwareChunker.chunk_document_sections(
        raw_text=doc_text,
        doc_title="Core Spec",
        max_words=100,
        min_tokens=10,
    )
    assert len(chunks) >= 2
    for chunk in chunks:
        assert "[Core Spec > " in chunk["text"]
        assert len(chunk["text"].split()) >= 10


def test_structure_aware_chunker_graph_triplets():
    triplets = [
        {"id": "project:foundation", "relation": "DEPENDS_ON", "label": "Project"},
        {"id": "person:priya", "relation": "LEADS", "label": "Person"},
        {"id": "decision:dec-0042", "relation": "IMPLEMENTS", "label": "Decision"},
    ]
    triplet_chunks = StructureAwareChunker.chunk_graph_triplets(
        source_id="project:titan",
        source_label="Project",
        triplets=triplets,
        max_per_chunk=2,
    )
    assert len(triplet_chunks) == 2
    assert "Project (project:titan) DEPENDS_ON Project (project:foundation)" in triplet_chunks[0]
    assert "Project (project:titan) LEADS Person (person:priya)" in triplet_chunks[0]
    assert "IMPLEMENTS Decision (decision:dec-0042)" in triplet_chunks[1]


@pytest.mark.asyncio
async def test_vector_indexer_document_15_field_payload(indexer):
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    text = "# System Blueprint\nThe system blueprint outlines high-throughput microservices using asynchronous event buses and decentralized storage nodes across multiple availability zones."
    metadata = {
        "classification": "Confidential",
        "department": "Infrastructure",
        "author_id": "usr_99",
        "project_id": "proj_omega",
        "completeness_score": 0.95,
        "data_quality_grade": "A",
        "validation_status": "valid",
    }

    count = await indexer.index_document(
        document_id=doc_id,
        text=text,
        metadata=metadata,
        doc_title="Blueprint",
    )
    assert count > 0

    # Search and verify 15-field payload
    search_hits = await indexer.search(
        query="system blueprint microservices asynchronous event",
        limit=5,
        filter_dict={"document_id": doc_id},
    )
    assert len(search_hits) > 0
    hit_payload = search_hits[0]["payload"]
    assert hit_payload["document_id"] == doc_id
    assert hit_payload["classification"] == "Confidential"
    assert hit_payload["department"] == "Infrastructure"
    assert hit_payload["data_quality_grade"] == "A"
    assert hit_payload["completeness_score"] == 0.95
    assert "text" in hit_payload
    assert "created_at" in hit_payload


@pytest.mark.asyncio
async def test_vector_indexer_entity_with_1hop_neighbors(indexer):
    ent_id = f"person_{uuid.uuid4().hex[:8]}"
    properties = {
        "name": "Dr. Ananya Roy",
        "role": "Principal Scientist",
        "department": "Research",
        "skills": ["NLP", "Transformers", "Ontology"],
    }
    neighbors = [
        {"id": "proj_nlp_core", "relation": "LEADS", "label": "Project"}
    ]
    metadata = {
        "classification": "Internal",
        "department": "Research",
        "completeness_score": 1.0,
        "data_quality_grade": "A",
    }

    point_id = await indexer.index_entity(
        entity_id=ent_id,
        entity_class="Person",
        properties=properties,
        metadata=metadata,
        graph_neighbors=neighbors,
    )
    assert point_id is not None

    # Search by skills and verify neighbor in payload
    hits = await indexer.search(
        query="Principal Scientist Transformers NLP Ontology",
        limit=5,
        filter_dict={"entity_id": ent_id},
    )
    assert len(hits) > 0
    payload = hits[0]["payload"]
    assert payload["entity_id"] == ent_id
    assert payload["entity_class"] == "Person"
    assert len(payload["graph_neighbors"]) == 1
    assert payload["graph_neighbors"][0]["id"] == "proj_nlp_core"
    assert payload["graph_neighbors"][0]["relation"] == "LEADS"


@pytest.mark.asyncio
async def test_cascade_reindexing_service(cascade_service, repo, indexer):
    # Create entity in FalkorDB
    node_id = f"inc_{uuid.uuid4().hex[:8]}"
    cause_id = f"cause_{uuid.uuid4().hex[:8]}"

    await repo.upsert_universal_node("Incident", node_id, {
        "title": "Cascaded Outage Event",
        "severity": "P1",
        "confirmed_cause": "BGP Hijack",
    })
    await repo.upsert_universal_node("Incident", cause_id, {
        "title": "BGP Hijack",
        "severity": "P2",
    })
    await repo.upsert_universal_edge(node_id, cause_id, "CAUSED_BY")

    # Trigger cascade re-indexing
    reindexed_count = await cascade_service.handle_downstream_invalidation(
        affected_node_ids=[node_id],
        triggered_by_node_id=cause_id,
    )
    assert reindexed_count == 1

    # Verify updated vector in Qdrant
    hits = await indexer.search(
        query="Cascaded Outage Event BGP Hijack",
        limit=5,
        filter_dict={"entity_id": node_id},
    )
    assert len(hits) > 0
    payload = hits[0]["payload"]
    assert payload["entity_id"] == node_id
    assert payload["recompute_triggered_by"] == cause_id
    assert len(payload["graph_neighbors"]) >= 1


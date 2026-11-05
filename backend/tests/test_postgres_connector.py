import pytest
from app.connectors.postgres.mapper import OntologyEntityMapper
from app.connectors.postgres.schema_discovery import PostgresSchemaDiscovery


def test_mapper_decision_entity():
    row = {
        "id": "dec_101",
        "title": "Migrate to Kubernetes",
        "context": "High traffic demands horizontal scaling",
        "rationale": "Better container management",
        "status": "APPROVED",
        "author": "Alice",
    }
    entity = OntologyEntityMapper.map_row_to_entity(
        row=row,
        connector_id="conn_abc",
        schema_name="public",
        table_name="decisions",
        entity_type="Decision",
        primary_key_cols=["id"],
        text_cols=["title", "context", "rationale"],
    )

    assert entity["entity_id"] == "pg:conn_abc:public:decisions:dec_101"
    assert entity["entity_class"] == "Decision"
    assert entity["label"] == "Migrate to Kubernetes"
    assert "High traffic demands" in entity["searchable_text"]
    assert entity["properties"]["status"] == "APPROVED"


def test_mapper_person_entity():
    row = {
        "user_id": "usr_99",
        "full_name": "Devin Engineer",
        "email": "devin@acme.com",
        "department": "Infrastructure",
    }
    entity = OntologyEntityMapper.map_row_to_entity(
        row=row,
        connector_id="conn_abc",
        schema_name="public",
        table_name="users",
        entity_type="Person",
        primary_key_cols=["user_id"],
        text_cols=["full_name", "email", "department"],
    )

    assert entity["entity_id"] == "pg:conn_abc:public:users:usr_99"
    assert entity["entity_class"] == "Person"
    assert entity["label"] == "Devin Engineer"
    assert entity["properties"]["email"] == "devin@acme.com"


def test_suggest_entity_type():
    assert PostgresSchemaDiscovery._suggest_entity_type("user_accounts", ["username", "email"]) == "Person"
    assert PostgresSchemaDiscovery._suggest_entity_type("architectural_decisions", ["title", "status"]) == "Decision"
    assert PostgresSchemaDiscovery._suggest_entity_type("incident_reports", ["severity", "impact"]) == "Incident"
    assert PostgresSchemaDiscovery._suggest_entity_type("postmortem_lessons", ["summary"]) == "Lesson"
    assert PostgresSchemaDiscovery._suggest_entity_type("systems_catalog", ["host", "ip"]) == "System"
    assert PostgresSchemaDiscovery._suggest_entity_type("other_random_data", ["col_a", "col_b"]) == "Document"

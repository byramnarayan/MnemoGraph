import pytest
from app.services.parsers.document_parser import DocumentParser
from app.services.enrichment.entity_extractor import EntityExtractor
from app.services.enrichment.relationship_extractor import RelationshipExtractor
from datetime import datetime, timezone, timedelta


def test_document_parser_structured_json():
    json_bytes = b'{"assigned_to": "Dr. Priya Sharma", "status": "active", "due_date": "2024-06-30"}'
    result = DocumentParser.parse_file("task.json", json_bytes)
    assert result.structuredness == "STRUCTURED"
    assert result.format == "application/json"
    assert result.inferred_fields.get("inferred_person") == "Dr. Priya Sharma"
    assert result.inferred_fields.get("inferred_status") == "active"


def test_document_parser_semi_structured_markdown():
    md_content = """# Architecture Review
Author: Vikram Rao
Date: 2024-03-12

| Service | Status | Owner |
| AuthGateway | Active | Platform Team |
| CoreEngine | Testing | Backend Team |

```python
def health_check():
    return {"status": "ok"}
```
"""
    result = DocumentParser.parse_file("architecture.md", md_content.encode("utf-8"))
    assert result.structuredness == "SEMI_STRUCTURED"
    assert len(result.tables) >= 1
    assert len(result.code_blocks) >= 1


def test_entity_extractor_universal_classes_and_stubs():
    text = """
    Incident INC-1024 occurred during deployment.
    Lead: Dr. Priya Sharma
    Team: Platform Team
    Project: Project Titan
    Decision decided to rollback change to MX480
    Task TASK-501 is assigned to UnknownEngineer.
    """
    extractor = EntityExtractor()
    entities, stubs, conflicts = extractor.extract_entities(text, document_id="doc-test-1")

    entity_classes = {e.entity_class for e in entities}
    assert "Incident" in entity_classes
    assert "Person" in entity_classes
    assert "Group" in entity_classes
    assert "Project" in entity_classes
    assert "Decision" in entity_classes
    assert "Task" in entity_classes

    # Verify STUB generation for dangling reference "UnknownEngineer"
    stub_labels = [s.label for s in stubs]
    assert any("UnknownEngineer" in lbl for lbl in stub_labels)
    for s in stubs:
        assert s.is_stub is True
        assert s.validation_status == "pending"


def test_entity_extractor_temporal_coherence():
    extractor = EntityExtractor()
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=2)

    # Valid: start earlier, resolution now
    is_valid, status = extractor.validate_temporal_coherence(earlier, now, "inc-valid")
    assert is_valid is True
    assert status == "valid"

    # Temporal conflict: resolution earlier than start
    is_valid, status = extractor.validate_temporal_coherence(now, earlier, "inc-conflict")
    assert is_valid is False
    assert status == "TEMPORAL_CONFLICT"


def test_entity_completeness_scoring():
    extractor = EntityExtractor()
    # Sparse person (name only)
    sparse_text = "Lead: Alice Smith"
    entities, _, _ = extractor.extract_entities(sparse_text, document_id="doc-test-sparse")
    person_ent = next(e for e in entities if e.entity_class == "Person")
    assert person_ent.completeness_score >= 0.5
    assert person_ent.data_quality_grade in ["A", "B", "C", "D"]


def test_relationship_extractor_taxonomy():
    text = """
    Dr. Priya Sharma leads Project Titan.
    Project Titan depends on CoreEngine.
    Incident INC-1024 caused by Change CHG-401.
    """
    entity_extractor = EntityExtractor()
    entities, stubs, _ = entity_extractor.extract_entities(text, document_id="doc-test-rel")

    rel_extractor = RelationshipExtractor()
    relationships = rel_extractor.extract_relationships(text, document_id="doc-test-rel", entities=entities + stubs)

    rel_types = {r.relationship_type for r in relationships}
    assert "LEADS" in rel_types
    assert "DEPENDS_ON" in rel_types
    assert "CAUSED_BY" in rel_types
    assert "DOCUMENTS" in rel_types

    for r in relationships:
        assert r.confidence > 0.0
        assert r.source_document_id == "doc-test-rel"


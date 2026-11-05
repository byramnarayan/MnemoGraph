from typing import Any
from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question or query")
    user_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    limit: int = Field(5, ge=1, le=20)
    classification_clearance: str | None = Field("Internal", description="User clearance level")


class EvidenceItem(BaseModel):
    document_id: str
    source_url: str
    excerpt: str
    score: float
    entity_type: str
    entity_id: str
    related_people: list[str] = Field(default_factory=list)
    related_teams: list[str] = Field(default_factory=list)
    related_projects: list[str] = Field(default_factory=list)


class SourceEvidence(BaseModel):
    entity_id: str
    entity_class: str
    label: str
    excerpt: str
    vector_score: float = 1.0
    graph_path: list[dict[str, Any]] = Field(default_factory=list)
    data_quality_grade: str = "A"      # "A", "B", "C", "D" (from IR-08)
    causal_chain_depth: int = 0         # from IR-01
    validation_status: str = "valid"   # "valid", "temporal_conflict" (from IR-05)
    recurrence_risk: bool = False       # from IR-06


class InferenceInsight(BaseModel):
    rule_id: str
    finding: str
    affected_entities: list[str] = Field(default_factory=list)


class MissingDataGap(BaseModel):
    entity_id: str
    missing_fields: list[str] = Field(default_factory=list)
    data_quality_grade: str = "D"


class CascadeWarning(BaseModel):
    entity_id: str
    reason: str
    triggered_by: str


class GraphAlgorithmEvidence(BaseModel):
    algorithm_name: str | None = None
    algorithm_version: str = "1.0"
    query_intent: str
    anchor_entity_ids: list[str] = Field(default_factory=list)
    paths: list[dict[str, Any]] = Field(default_factory=list)
    metric_values: dict[str, float] = Field(default_factory=dict)
    community_memberships: dict[str, int] = Field(default_factory=dict)
    traversal_depth: int = 0
    computed_at: str | None = None
    data_quality_warnings: list[str] = Field(default_factory=list)


class UKGOEAnswerResponse(BaseModel):
    answer_text: str
    intent: str = "FACTUAL"
    confidence: float
    sources: list[SourceEvidence] = Field(default_factory=list)
    inference_insights: list[InferenceInsight] = Field(default_factory=list)
    graph_query_used: str | None = None
    missing_data_gaps: list[MissingDataGap] = Field(default_factory=list)
    cascade_warnings: list[CascadeWarning] = Field(default_factory=list)
    algorithm_evidence: list[GraphAlgorithmEvidence] = Field(default_factory=list)
    # UKGOE Feature B Predictive Intelligence
    predictive_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    timeline_events: list[dict[str, Any]] = Field(default_factory=list)
    decision_summaries: list[dict[str, Any]] = Field(default_factory=list)
    forecast_result: dict[str, Any] | None = None


class AnswerResponse(BaseModel):
    answer_text: str
    source_document_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    related_people: list[str] = Field(default_factory=list)
    related_teams: list[str] = Field(default_factory=list)
    related_projects: list[str] = Field(default_factory=list)
    relation_path: list[dict] = Field(default_factory=list)
    confidence: float
    evidence: list[EvidenceItem] = Field(default_factory=list)
    graph_query: str | None = Field(default=None, description="Executable Cypher query representing this answer provenance graph")
    # UKGOE Phase 5 extended fields
    intent: str | None = None
    sources: list[SourceEvidence] = Field(default_factory=list)
    inference_insights: list[InferenceInsight] = Field(default_factory=list)
    missing_data_gaps: list[MissingDataGap] = Field(default_factory=list)
    cascade_warnings: list[CascadeWarning] = Field(default_factory=list)
    algorithm_evidence: list[GraphAlgorithmEvidence] = Field(default_factory=list)
    # UKGOE Feature B Predictive Intelligence
    predictive_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    timeline_events: list[dict[str, Any]] = Field(default_factory=list)
    decision_summaries: list[dict[str, Any]] = Field(default_factory=list)
    forecast_result: dict[str, Any] | None = None


class ContextAnswerRequest(BaseModel):
    query: str = Field(..., min_length=2)
    entity_id: str = Field(..., description="Entity ID to explain context for (e.g. decision ID, document ID)")
    user_id: str | None = None


class LLMAnswerRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question")
    user_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    context: dict | None = None


class LLMAnswerResponse(BaseModel):
    answer_text: str
    source_document_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    related_people: list[str] = Field(default_factory=list)
    related_teams: list[str] = Field(default_factory=list)
    related_projects: list[str] = Field(default_factory=list)
    relation_path: list[dict] = Field(default_factory=list)
    confidence: float

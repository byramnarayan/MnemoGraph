from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question or query")
    user_id: str | None = None
    workspace_id: str | None = None
    project_id: str | None = None
    limit: int = Field(5, ge=1, le=20)


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


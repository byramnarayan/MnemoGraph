from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DecisionCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    source_document_id: str | None = None
    created_by_user_id: str | None = None
    status: str = "accepted"


class DecisionCreateResponse(BaseModel):
    id: str
    title: str
    status: str


class DecisionLinkCreateRequest(BaseModel):
    related_entity_type: str = Field(..., description="Document, Person, Team, Project, Task, Ticket, Meeting, Artifact")
    related_entity_id: str
    relation_type: str = Field("RELATED_TO", description="DERIVED_FROM, CREATED_BY, RELATED_TO, REFERENCES, etc.")


class DecisionLinkResponse(BaseModel):
    ok: bool = True
    message: str | None = None


class DecisionDetailResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: str
    impact: str | None = None
    learnings: str | None = None
    timeline: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    source_document_id: str | None = None
    created_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime

    related_project: dict | None = None
    source_document: dict | None = None
    created_by_person: dict | None = None
    related_teams: list[dict] = Field(default_factory=list)
    related_docs: list[dict] = Field(default_factory=list)
    related_tasks: list[dict] = Field(default_factory=list)
    related_tickets: list[dict] = Field(default_factory=list)
    related_meetings: list[dict] = Field(default_factory=list)
    related_artifacts: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RelationPath(BaseModel):
    from_entity: str = Field(..., alias="from")
    to_entity: str = Field(..., alias="to")
    relation: str

    model_config = ConfigDict(populate_by_name=True)


class DecisionProvenanceResponse(BaseModel):
    decision_id: str
    decision_title: str
    source_documents: list[dict] = Field(default_factory=list)
    related_people: list[dict] = Field(default_factory=list)
    related_teams: list[dict] = Field(default_factory=list)
    related_projects: list[dict] = Field(default_factory=list)
    related_tasks: list[dict] = Field(default_factory=list)
    related_tickets: list[dict] = Field(default_factory=list)
    related_meetings: list[dict] = Field(default_factory=list)
    related_artifacts: list[dict] = Field(default_factory=list)
    relation_paths: list[RelationPath] = Field(default_factory=list)


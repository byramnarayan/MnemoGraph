from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class IncidentSummaryItem(BaseModel):
    incident_id: str
    title: str
    severity: str | None = None
    type: str | None = None
    status: str | None = "open"
    cause_status: str | None = None
    data_quality_grade: str = "B"
    view_count: int = 0
    last_viewed_at: str | None = None


# --- Individual Layer Schemas ---

class Layer0IncidentHeader(BaseModel):
    incident_id: str
    title: str
    severity: str | None = None
    type: str | None = None
    status: str | None = None
    cause_status: str | None = None
    confirmed_cause: str | None = None
    initial_suspected_cause: str | None = None
    cause_revision_note: str | None = None
    is_misdiagnosed: bool = False
    recurrence_risk: bool = False
    recurrence_count: int = 0
    causal_chain_depth: int = 0
    data_quality_grade: str = "B"
    classification: str = "Internal"
    view_count: int = 0
    last_viewed_at: str | None = None


class Layer1ImmediateCauses(BaseModel):
    cause_decisions: list[dict[str, Any]] = Field(default_factory=list)
    cause_changes: list[dict[str, Any]] = Field(default_factory=list)
    prior_incidents: list[dict[str, Any]] = Field(default_factory=list)
    linked_project: dict[str, Any] | None = None


class Layer2AffectedScope(BaseModel):
    affected_systems: list[dict[str, Any]] = Field(default_factory=list)
    affected_locations: list[dict[str, Any]] = Field(default_factory=list)
    linked_project_context: dict[str, Any] | None = None


class Layer3CorrectiveTasks(BaseModel):
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class Layer4RecurrenceChain(BaseModel):
    backward_recurrence: list[dict[str, Any]] = Field(default_factory=list)
    forward_recurrence: list[dict[str, Any]] = Field(default_factory=list)


class Layer5PeopleInvolved(BaseModel):
    task_assignees: list[dict[str, Any]] = Field(default_factory=list)
    decision_makers: list[dict[str, Any]] = Field(default_factory=list)
    project_leads: list[dict[str, Any]] = Field(default_factory=list)


class Layer6Documents(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)


class Layer7LessonsLearned(BaseModel):
    lessons: list[dict[str, Any]] = Field(default_factory=list)


class Layer8SimilarIncidents(BaseModel):
    similar_incidents: list[dict[str, Any]] = Field(default_factory=list)


# --- Full Envelope ---

class IncidentInterconnectResponse(BaseModel):
    incident_id: str
    access_level: int
    access_level_description: str
    user_clearance: str
    layer0_incident: Layer0IncidentHeader
    layer1_causes: Layer1ImmediateCauses | None = None
    layer2_affected_scope: Layer2AffectedScope | None = None
    layer3_tasks: Layer3CorrectiveTasks | None = None
    layer4_recurrence: Layer4RecurrenceChain | None = None
    layer5_people: Layer5PeopleInvolved | None = None
    layer6_documents: Layer6Documents | None = None
    layer7_lessons: Layer7LessonsLearned | None = None
    layer8_similar_incidents: Layer8SimilarIncidents | None = None


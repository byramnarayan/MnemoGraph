from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class KTPCandidateResponse(BaseModel):
    person_id: str
    full_name: str
    role: str | None = None
    group: str | None = None
    employment_status: str
    ktp_generated: bool = False
    ktp_doc_id: str | None = None
    ktp_generated_at: str | None = None


class KtpPersonSummary(BaseModel):
    person_id: str
    full_name: str
    role: str | None = None
    group: str | None = None
    location: str | None = None
    employment_status: str = "active"
    clearance_level: str = "Internal"
    ktp_generated: bool = False
    ktp_doc_id: str | None = None
    ktp_generated_at: str | None = None
    concentration_risk: bool = False
    active_projects_count: int = 0
    open_tasks_count: int = 0
    is_handed_over_to_me: bool = False


class AssignHandoverRequest(BaseModel):
    target_person_id: str
    notes: str | None = None


class AssignHandoverResponse(BaseModel):
    success: bool = True
    message: str
    source_person_id: str
    target_person_id: str
    assigned_at: str


# --- Section Models ---

class SectionAPersonProfile(BaseModel):
    person_id: str
    full_name: str
    current_role: str | None = None
    current_group: str | None = None
    location: str | None = None
    role_history: list[dict[str, Any]] = Field(default_factory=list)
    manager_chain: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class SectionBActiveOwnership(BaseModel):
    active_projects: list[dict[str, Any]] = Field(default_factory=list)
    active_tasks: list[dict[str, Any]] = Field(default_factory=list)


class SectionCDecisionHistory(BaseModel):
    decisions_made: list[dict[str, Any]] = Field(default_factory=list)
    decisions_contributed: list[dict[str, Any]] = Field(default_factory=list)


class SectionDIncidentInvolvement(BaseModel):
    incidents_as_task_assignee: list[dict[str, Any]] = Field(default_factory=list)
    incidents_as_project_lead: list[dict[str, Any]] = Field(default_factory=list)


class SectionEKnowledgeAuthored(BaseModel):
    authored_documents: list[dict[str, Any]] = Field(default_factory=list)
    lessons_learned: list[dict[str, Any]] = Field(default_factory=list)


class SectionFRiskFlags(BaseModel):
    concentration_risk_score: float = 0.0
    recurrence_risk_tasks: list[dict[str, Any]] = Field(default_factory=list)
    overdue_tasks: list[dict[str, Any]] = Field(default_factory=list)
    documentation_gaps: list[dict[str, Any]] = Field(default_factory=list)


class SuccessorCandidate(BaseModel):
    person_id: str
    full_name: str
    role: str | None = None
    group: str | None = None
    shared_skills: list[str] = Field(default_factory=list)
    skill_overlap_count: int = 0


class SectionGHandoverRecommendations(BaseModel):
    tasks_to_reassign: list[dict[str, Any]] = Field(default_factory=list)
    projects_needing_lead_or_contributor: list[dict[str, Any]] = Field(default_factory=list)
    sole_author_documents: list[dict[str, Any]] = Field(default_factory=list)
    successor_candidates: list[SuccessorCandidate] = Field(default_factory=list)


# --- Full KTP Response ---

class KnowledgeTransferPackageResponse(BaseModel):
    doc_id: str
    subject_person_id: str
    subject_person_name: str
    requestor_id: str
    requestor_role: str
    generated_at: str
    classification: str = "Internal"
    is_stale: bool = False
    cascade_warning: str | None = None
    referenced_entity_ids: list[str] = Field(default_factory=list)

    section_a_profile: SectionAPersonProfile | None = None
    section_b_ownership: SectionBActiveOwnership | None = None
    section_c_decisions: SectionCDecisionHistory | None = None
    section_d_incidents: SectionDIncidentInvolvement | None = None
    section_e_knowledge: SectionEKnowledgeAuthored | None = None
    section_f_risks: SectionFRiskFlags | None = None
    section_g_handover: SectionGHandoverRecommendations | None = None


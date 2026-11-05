export interface KtpPersonSummary {
  person_id: string;
  full_name: string;
  role: string | null;
  group: string | null;
  location: string | null;
  employment_status: string;
  clearance_level: string;
  ktp_generated: boolean;
  ktp_doc_id: string | null;
  ktp_generated_at: string | null;
  concentration_risk: boolean;
  active_projects_count: number;
  open_tasks_count: number;
  is_handed_over_to_me: boolean;
}

export interface SectionAPersonProfile {
  person_id: string;
  full_name: string;
  current_role: string | null;
  current_group: string | null;
  location: string | null;
  role_history: Array<{
    title: string;
    start_date: string | null;
    end_date: string | null;
    department: string;
  }>;
  manager_chain: Array<{
    manager_id: string;
    name: string;
    role: string | null;
    depth: number;
  }>;
  skills: string[];
}

export interface SectionBActiveOwnership {
  active_projects: Array<{
    project_id: string;
    name: string;
    relationship: string;
    status: string;
    milestones: Array<{
      id: string;
      name: string;
      status: string;
      target_date: string | null;
    }>;
    linked_decisions: Array<{
      id: string;
      title: string;
      outcome: string | null;
    }>;
    linked_incidents: Array<{
      id: string;
      title: string;
      severity: string | null;
    }>;
  }>;
  active_tasks: Array<{
    task_id: string;
    title: string;
    status: string;
    due_date: string | null;
    effectiveness_label: string | null;
    source_entity: {
      id: string;
      labels: string[];
    } | null;
  }>;
}

export interface SectionCDecisionHistory {
  decisions_made: Array<{
    decision_id: string;
    title: string;
    outcome: string | null;
    decision_type: string | null;
    decision_date: string | null;
    root_cause_analysis: string | null;
    linked_project_status: string | null;
    open_tasks_count: number;
  }>;
  decisions_contributed: Array<{
    decision_id: string;
    title: string;
    outcome: string | null;
    project_name: string | null;
  }>;
}

export interface SectionDIncidentInvolvement {
  incidents_as_task_assignee: Array<{
    incident_id: string;
    title: string;
    severity: string | null;
    type: string | null;
    cause_status: string | null;
    tasks: Array<{
      task_id: string;
      title: string;
      status: string;
    }>;
    pir_documents: Array<{
      id: string;
      title: string;
    }>;
  }>;
  incidents_as_project_lead: Array<{
    incident_id: string;
    title: string;
    severity: string | null;
    type: string | null;
    cause_status: string | null;
    project_name: string | null;
  }>;
}

export interface SectionEKnowledgeAuthored {
  authored_documents: Array<{
    document_id: string;
    title: string;
    document_type: string | null;
    status: string | null;
    creation_date: string | null;
    successor_document_id: string | null;
  }>;
  lessons_learned: Array<{
    lesson_id: string;
    title: string;
    project_id: string | null;
    summary: string | null;
  }>;
}

export interface SectionFRiskFlags {
  concentration_risk_score: number;
  recurrence_risk_tasks: Array<any>;
  overdue_tasks: Array<any>;
  documentation_gaps: Array<{
    id: string;
    title: string;
    labels: string[];
  }>;
}

export interface SuccessorCandidate {
  person_id: string;
  full_name: string;
  role: string | null;
  group: string | null;
  shared_skills: string[];
  skill_overlap_count: number;
}

export interface SectionGHandoverRecommendations {
  tasks_to_reassign: Array<any>;
  projects_needing_lead_or_contributor: Array<any>;
  sole_author_documents: Array<any>;
  successor_candidates: SuccessorCandidate[];
}

export interface KnowledgeTransferPackageResponse {
  doc_id: string;
  subject_person_id: string;
  subject_person_name: string;
  requestor_id: string;
  requestor_role: string;
  generated_at: string;
  classification: string;
  is_stale: boolean;
  cascade_warning: string | null;
  referenced_entity_ids: string[];
  section_a_profile: SectionAPersonProfile | null;
  section_b_ownership: SectionBActiveOwnership | null;
  section_c_decisions: SectionCDecisionHistory | null;
  section_d_incidents: SectionDIncidentInvolvement | null;
  section_e_knowledge: SectionEKnowledgeAuthored | null;
  section_f_risks: SectionFRiskFlags | null;
  section_g_handover: SectionGHandoverRecommendations | null;
}

export interface AssignHandoverRequest {
  target_person_id: string;
  notes?: string;
}

export interface AssignHandoverResponse {
  success: boolean;
  message: string;
  source_person_id: string;
  target_person_id: string;
  assigned_at: string;
}


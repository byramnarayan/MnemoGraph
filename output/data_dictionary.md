# Data Dictionary — Aarohan Digital Networks Limited Synthetic Dataset

## CompanyProfile
| Field | Type | Description |
|-------|------|-------------|
| company_name | str | Legal name of the fictional telecom company |
| cin | str (21 chars) | Synthetic Corporate Identification Number |
| incorporation_date | date | Date the company was incorporated |
| registered_city | str | City of registered office |
| description | str (50–300) | Company description |
| office_locations | list[SiteLocation] | Physical office locations (min 6) |
| service_types | list[str] | Telecom services offered (min 4) |

## SiteLocation
| Field | Type | Description |
|-------|------|-------------|
| id | str (SITE-XXXX) | Unique site identifier |
| city | str | Indian city name |
| address | str | Street address |

## Department
| Field | Type | Description |
|-------|------|-------------|
| id | str (DEPT-XXXX) | Unique department identifier |
| name | str | Department name (from allowed list) |
| description | str | Department function description |

## Team
| Field | Type | Description |
|-------|------|-------------|
| id | str (TEAM-XXXX) | Unique team identifier |
| name | str | Team name |
| department_id | str | Parent department FK |
| primary_site_id | str | Primary office location FK |

## Employee
| Field | Type | Description |
|-------|------|-------------|
| id | str (EMP-XXXX) | Unique employee identifier |
| full_name | str | Full name (Indian locale) |
| gender | str | Gender |
| date_of_birth | date | Date of birth |
| hire_date | date | Date joined Aarohan |
| current_job_title | str | Current role title |
| current_department_id | str | Current department FK |
| current_team_id | str | Current team FK |
| current_manager_id | str | Current manager EMP FK |
| employment_status | enum | active / on_leave / terminated |
| primary_site_id | str | Primary office SITE FK |
| role_history | list[RoleHistory] | Career history (2–10 entries) |
| is_focal | bool | True for the single focal employee |
| skills | list[str] | Technical/professional skills (JSONB) |

## RoleHistory
| Field | Type | Description |
|-------|------|-------------|
| start_date | date | Role start date |
| end_date | date\|null | Role end date (null = current role) |
| job_title | str | Title at this point in career |
| team_id | str | Team TEAM FK |
| manager_id | str | Manager EMP FK at this time |
| reason | enum | promotion / lateral_move / restructure / new_hire |

## Project
| Field | Type | Description |
|-------|------|-------------|
| id | str (PROJ-XXXX) | Unique project identifier |
| name | str | Project name |
| description | str | Project description |
| sponsoring_department_id | str | Sponsoring department FK |
| lead_emp_id | str | Project lead EMP FK |
| team_emp_ids | list[str] | Team member EMP FKs (JSONB, min 3) |
| start_date | date | Project start date |
| planned_end_date | date | Original planned completion |
| actual_end_date | date\|null | Actual completion (null if active/on-hold) |
| status | enum | active / completed / cancelled / on-hold |
| outcome_summary | str (min 50) | Summary of project outcome |
| milestones | list[Milestone] | Project milestones (3–7) |
| causal_incident_id | str\|null | Incident that caused on-hold/cancelled |
| causal_decision_id | str\|null | Decision that caused on-hold/cancelled |
| lessons_learned | list[LessonLearned] | Lessons from completed/cancelled projects |

## Decision
| Field | Type | Description |
|-------|------|-------------|
| id | str (DEC-XXXX) | Unique decision identifier |
| title | str | Decision title |
| description | str | Decision description |
| decision_date | date | Date decision was made |
| decision_type | enum | technical / operational / strategic / financial |
| outcome | enum | positive / neutral / negative |
| rationale | str (min 80) | Rationale for the decision |
| alternatives_considered | list[str] (2–5) | Options evaluated and rejected |
| deciding_emp_id | str | Decision maker EMP FK |
| project_id | str\|null | Linked project PROJ FK |
| root_cause_analysis | str\|null (80–1000) | RCA for negative outcomes |

## Incident
| Field | Type | Description |
|-------|------|-------------|
| id | str (INC-XXXX) | Unique incident identifier |
| title | str (10–100) | Incident title |
| description | str (50–500) | Incident description |
| incident_type | enum | outage / config_error / billing_discrepancy / security_near_miss / performance_degradation |
| severity | enum | P1 / P2 / P3 / P4 |
| start_datetime | datetime (UTC) | When incident started |
| resolution_datetime | datetime\|null | When incident was resolved |
| affected_services | list[str] | SVC- IDs affected (JSONB) |
| affected_sites | list[str] | SITE- IDs affected (JSONB) |
| initial_suspected_cause | str (10–200) | Initial NOC hypothesis |
| confirmed_cause | str\|null (10–200) | Evidence-based root cause |
| cause_status | enum | suspected / confirmed |
| cause_revision_note | str\|null (10–300) | Explanation of cause revision |
| project_id | str\|null | Linked project PROJ FK |

## FollowUpAction
| Field | Type | Description |
|-------|------|-------------|
| id | str (ACT-XXXX) | Unique action identifier |
| title | str (10–100) | Action title |
| description | str (30–300) | Action description |
| source_type | literal | "incident" or "decision" |
| source_id | str | Source INC- or DEC- FK |
| assigned_emp_id | str | Assigned employee EMP FK |
| due_date | date | Target completion date |
| completion_date | date\|null | Actual completion date |
| status | enum | open / in-progress / completed / overdue |
| effectiveness_label | enum | prevented_recurrence / partially_effective / ineffective / not_yet_assessed |
| recurrence_incident_id | str\|null | Recurrence INC FK for ineffective actions |

## BusinessDocument
| Field | Type | Description |
|-------|------|-------------|
| id | str (DOC-XXXX) | Unique document identifier |
| title | str | Document title |
| document_type | enum | project_charter / PIR / ADR / CAT / lessons_learned_report / quarterly_review / rca_report / risk_register |
| body | str (min 200) | Document body text |
| creation_date | date | Date document was created |
| author_emp_id | str | Author EMP FK |
| status | enum | draft / approved / superseded |
| referenced_entity_ids | list[str] (min 1) | Referenced entity IDs (JSONB) |
| successor_doc_id | str\|null | Superseding document DOC FK |

## RelationshipEntry
| Field | Type | Description |
|-------|------|-------------|
| source_id | str | Source entity ID |
| target_id | str | Target entity ID |
| relationship_type | str | Relationship label |
| context | str (5–120) | Human-readable relationship description |

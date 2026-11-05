export interface DecisionRiskSummary {
  decision_id: string;
  decision_title: string;
  decision_date?: string | null;
  decision_maker?: string | null;
  affected_systems: string[];
  incident_probability: number;
  risk_tier: 'CRITICAL' | 'ELEVATED' | 'MODERATE' | 'LOW' | string;
  predicted_horizon_days: string;
  lanobert_score: number;
  bottleneck_score: number;
  unimplemented_action_count: number;
  tasks_summary?: Array<{
    id?: string;
    title?: string;
    status?: string;
    due_date?: string;
  }>;
}

export interface DecisionDeepDiveNarrative {
  decision_id: string;
  decision_title: string;
  incident_probability: number;
  risk_tier: string;
  predicted_horizon: string;
  executive_scenario: string;
  narrative_timeline: string;
  interconnected_context: string;
  lessons_learned: string;
  recommended_action: {
    action_title: string;
    action_type: string;
    suggested_role: string;
    priority: string;
    implementation_steps: string[];
    verification_criteria: string;
  };
  evidence_citations: Array<{
    id: string;
    source: string;
    detail: string;
  }>;
}

export interface RecommendedAction {
  action_title: string;
  action_type: string;
  suggested_role: string;
  priority: string;
  rationale: string;
  historical_precedent_action?: string | null;
  historical_outcome?: string | null;
  implementation_steps: string[];
  verification_criteria: string;
}

export interface PredictiveScenario {
  scenario_id: string;
  scenario_title: string;
  affected_scope: string;
  possible_incident_type: string;
  forecast_horizon_days: number;
  forecast_probability: number;
  predicted_interval: string;
  uncertainty_level: string;
  contributing_factors: string[];
  historical_precedent?: {
    incident_id: string;
    incident_title: string;
    action_effectiveness?: string;
  };
  recommended_action: RecommendedAction;
  evidence_citation_ids: string[];
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  entity_id: string;
  entity_name: string;
  timestamp_str?: string | null;
  actor_name?: string | null;
  affected_scope?: string | null;
  relation_semantics: string;
  details?: Record<string, any>;
}

export interface DecisionFollowUpSummary {
  decision_id: string;
  decision_title: string;
  decision_date?: string | null;
  decision_maker?: string | null;
  related_action_title?: string | null;
  action_deployment_date?: string | null;
  affected_scope?: string | null;
  follow_up_days: number;
  follow_up_status: string;
  observation_note: string;
  evidence_coverage: string;
}

export interface HorizonForecast {
  horizon_days: number;
  incident_probability: number;
  cumulative_risk_label: string;
}

export interface IncidentForecastResult {
  entity_id: string;
  entity_scope: string;
  forecast_status: string;
  horizons: HorizonForecast[];
  predicted_interval_days: string;
  forecast_confidence: number;
  uncertainty_level: string;
  lanobert_anomaly_score: number;
  graph_centrality_score: number;
  rule_risk_signals_count: number;
}

export interface PredictivePayload {
  answer_text: string;
  confidence: number;
  forecast_result?: IncidentForecastResult;
  predictive_scenarios?: PredictiveScenario[];
  decision_summaries?: DecisionFollowUpSummary[];
  timeline_events?: TimelineEvent[];
}


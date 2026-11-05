export interface SourceEvidenceItem {
  entity_id: string;
  entity_class: string;
  label?: string;
  excerpt: string;
  vector_score: number;
  data_quality_grade?: 'A' | 'B' | 'C' | 'D' | string;
  causal_chain_depth?: number;
  validation_status?: string;
  recurrence_risk?: boolean;
  graph_neighbors?: Array<{
    id: string;
    relation: string;
    label: string;
  }>;
  graph_path?: any[];
  source_document_id?: string;
}

export interface InferenceInsightItem {
  rule_id: string;
  finding: string;
  affected_entities: string[];
}

export interface MissingDataGapItem {
  entity_id: string;
  missing_fields: string[];
  data_quality_grade: string;
}

export interface CascadeWarningItem {
  entity_id: string;
  reason: string;
  triggered_by: string;
}

export interface UKGOEAnswerData {
  answer_text: string;
  intent: 'FACTUAL' | 'RELATIONAL' | 'CAUSAL' | 'PREDICTIVE' | 'COMPARATIVE' | 'AGGREGATIVE' | string;
  confidence: number;
  traversal_depth?: number;
  sources: SourceEvidenceItem[];
  inference_insights: InferenceInsightItem[];
  missing_data_gaps: MissingDataGapItem[];
  cascade_warnings: CascadeWarningItem[];
  graph_query_used?: string | null;
  graph_query?: string | null;
  predictive_scenarios?: PredictiveScenario[];
  timeline_events?: TimelineEvent[];
  decision_summaries?: DecisionFollowUpSummary[];
  forecast_result?: IncidentForecastResult | null;
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
  historical_precedent?: any;
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

export interface IncidentForecastResult {
  entity_id: string;
  entity_scope: string;
  forecast_status: string;
  horizons: Array<{
    horizon_days: number;
    incident_probability: number;
    cumulative_risk_label: string;
  }>;
  predicted_interval_days: string;
  forecast_confidence: number;
  uncertainty_level: string;
  lanobert_anomaly_score: number;
  graph_centrality_score: number;
  rule_risk_signals_count: number;
}

export interface UniversalCollection {
  id: string;
  name: string;
  store_type: 'FalkorDB' | 'PostgreSQL' | 'Object Storage' | 'Qdrant' | string;
  entity_count: number;
  description: string;
  can_delete: boolean;
  tier?: string;
}

export interface MemoryEpisode {
  id: string;
  session_id: string;
  query: string;
  answer: string;
  confidence: number;
  sources: any[];
  provenance: any[];
  cypher_query?: string;
  created_at: string;
}

export interface GraphNode {
  id: string;
  name?: string;
  label?: string;
  type?: string;
  score?: number;
  val?: number;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation?: string;
  type?: string;
  weight?: number;
}



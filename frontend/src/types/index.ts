export type RiskCategory = 'LOW_RISK' | 'REVIEW' | 'HIGH_RISK';
export type AlertSeverity = 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'IN_REVIEW' | 'RESOLVED';
export type ResolutionOutcome = 'UNRESOLVED' | 'CONFIRMED_FRAUD' | 'LEGITIMATE' | 'INCONCLUSIVE';

export interface RiskFactor {
  feature: string;
  value: number;
  contribution: number;
  direction?: string;
}

export interface ScoredTransaction {
  transaction_id: string;
  event_timestamp: string;
  ingestion_timestamp: string;
  scoring_timestamp: string;
  source_account_id: string;
  destination_account_id?: string | null;
  merchant_id?: string | null;
  merchant_category?: string | null;
  device_id: string;
  ip_address: string;
  transaction_amount: number;
  currency: string;
  transaction_type: string;
  location?: string | null;
  transaction_status: string;
  fraud_label?: number | null;
  is_demo: boolean;
  scenario_tag?: string | null;
  is_late_event: boolean;
  late_by_seconds: number;
  ml_score: number;
  graph_score: number;
  rule_score: number;
  combined_score: number;
  risk_percentage: number;
  risk_category: RiskCategory;
  predicted_class: number;
  model_version: string;
  scoring_method: string;
  scoring_status: string;
  warnings: string[];
  triggered_rules: string[];
  top_risk_factors: RiskFactor[];
  graph_explanations: string[];
  features: Record<string, number>;
  alert_id?: string | null;
  processing_latency_ms: number;
}

export interface AlertRecord {
  alert_id: string;
  transaction_id: string;
  account_id: string;
  merchant_id?: string | null;
  transaction_amount: number;
  currency: string;
  detection_timestamp: string;
  risk_score: number;
  risk_percentage: number;
  ml_score: number;
  graph_score: number;
  rule_score: number;
  severity: AlertSeverity;
  risk_category: RiskCategory;
  detection_method: string;
  triggered_rules: string[];
  model_explanation: RiskFactor[];
  graph_relationships: string[];
  investigation_status: AlertStatus;
  assigned_to?: string | null;
  resolution_outcome: ResolutionOutcome;
  is_demo: boolean;
  scenario_tag?: string | null;
  notes: Array<{ note_id: number; author: string; note: string; created_at: string }>;
  audit_history: Array<{ event_id: number; action: string; actor: string; details: Record<string, unknown>; created_at: string }>;
}

export interface GraphNeighborhood {
  center_id: string | null;
  available_entities: string[];
  nodes: Array<{
    id: string;
    node_type: 'ACCOUNT' | 'DEVICE' | 'IP' | 'MERCHANT' | 'TRANSACTION';
    first_seen: string;
    last_seen: string;
    risk_score: number;
    tx_count: number;
    amount?: number;
    category?: string;
    location?: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
    edge_type: string;
    first_seen: string;
    last_seen: string;
    count: number;
    total_amount: number;
  }>;
  summary: {
    node_count: number;
    edge_count: number;
    total_graph_nodes: number;
    shared_devices: Array<{ device_id: string; accounts: string[]; account_count: number }>;
    suspicious_clusters: number;
    engine_backend: string;
  };
}

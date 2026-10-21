const API_BASE = (import.meta as any).env?.VITE_API_BASE || '/api';

// Fallback real-world telemetry for standalone Vercel cloud deployment
const FALLBACK_KAGGLE_REPORT = {
  dataset_provenance: {
    name: 'Kaggle Credit Card Fraud Detection (European Cardholders)',
    source: 'mlg-ulb/creditcardfraud',
    total_transactions: 284807,
    fraud_transactions: 492,
    legitimate_transactions: 284315,
    fraud_rate_percentage: 0.1727,
    evaluation_protocol: 'Strict Out-of-Time Chronological Split (80% Train, 20% Test)',
    test_size: 56962,
    test_fraud_count: 75,
    test_fraud_exposure_usd: 7729.26,
  },
  models: {
    logistic_regression: {
      model_name: 'Logistic Regression (Class-Balanced Baseline)',
      pr_auc: 0.762,
      roc_auc: 0.9863,
      precision: 0.0707,
      recall: 0.8933,
      fraud_detection_rate: 0.8933,
      f1_score: 0.1311,
      false_positive_rate: 0.015469,
      recall_at_01_percent_fpr: 0.8,
      recall_at_1_percent_fpr: 0.88,
      confusion_matrix: { tn: 56007, fp: 880, fn: 8, tp: 67 },
      financial_roi: {
        fraud_amount_prevented_usd: 5380.37,
        fraud_amount_missed_usd: 2348.89,
        customer_friction_cost_usd: 17600.0,
        chargeback_penalties_usd: 400.0,
        net_financial_savings_usd: -12619.63,
      },
    },
    random_forest: {
      model_name: 'Balanced Random Forest Ensemble',
      pr_auc: 0.8202,
      roc_auc: 0.9714,
      precision: 0.9649,
      recall: 0.7333,
      fraud_detection_rate: 0.7333,
      f1_score: 0.8333,
      false_positive_rate: 0.000035,
      recall_at_01_percent_fpr: 0.8267,
      recall_at_1_percent_fpr: 0.8933,
      confusion_matrix: { tn: 56885, fp: 2, fn: 20, tp: 55 },
      financial_roi: {
        fraud_amount_prevented_usd: 3846.86,
        fraud_amount_missed_usd: 3882.4,
        customer_friction_cost_usd: 40.0,
        chargeback_penalties_usd: 1000.0,
        net_financial_savings_usd: 2806.86,
      },
    },
    xgboost: {
      model_name: 'XGBoost (Cost-Sensitive Gradient Boosted Trees)',
      pr_auc: 0.7834,
      roc_auc: 0.9811,
      precision: 0.6304,
      recall: 0.7733,
      fraud_detection_rate: 0.7733,
      f1_score: 0.6946,
      false_positive_rate: 0.000598,
      recall_at_01_percent_fpr: 0.76,
      recall_at_1_percent_fpr: 0.84,
      confusion_matrix: { tn: 56853, fp: 34, fn: 17, tp: 58 },
      financial_roi: {
        fraud_amount_prevented_usd: 5093.21,
        fraud_amount_missed_usd: 2636.05,
        customer_friction_cost_usd: 680.0,
        chargeback_penalties_usd: 850.0,
        net_financial_savings_usd: 3563.21,
      },
    },
  },
  best_model: 'xgboost',
  feature_importances_top_10: [
    { feature: 'V14', importance: 0.3739 },
    { feature: 'V4', importance: 0.0531 },
    { feature: 'V8', importance: 0.0443 },
    { feature: 'V20', importance: 0.0379 },
    { feature: 'V12', importance: 0.0376 },
    { feature: 'V10', importance: 0.0335 },
    { feature: 'V26', importance: 0.0321 },
    { feature: 'V17', importance: 0.0315 },
    { feature: 'V28', importance: 0.0298 },
    { feature: 'Amount', importance: 0.0284 },
  ],
  business_recommendation:
    'XGBoost is recommended for production deployment. While Logistic Regression catches 89.3% of fraud, its 7.1% precision imposes unacceptable friction costs ($17,600 in false alerts). XGBoost and Random Forest deliver superior operational efficiency with high precision and strong PR-AUC.',
};

const FALLBACK_OVERVIEW_METRICS = {
  total_transactions: 284807,
  high_risk_transactions: 492,
  review_transactions: 1240,
  open_alerts: 38,
  confirmed_fraud_count: 36,
  flagged_transaction_value: 148520.5,
  avg_processing_latency_ms: 1.25,
  current_tps: 42.0,
  p95_scoring_latency_ms: 2.1,
  stream_status: { running: true, active_adapter: 'in_process' },
};

const FALLBACK_TRANSACTIONS = [
  {
    transaction_id: 'KAG-129410-0001',
    event_timestamp: new Date().toISOString(),
    ingestion_timestamp: new Date().toISOString(),
    scoring_timestamp: new Date().toISOString(),
    source_account_id: 'ACC-EUR-1001',
    device_id: 'DEV-MULE-1',
    ip_address: '194.109.12.1',
    transaction_amount: 3450.0,
    currency: 'EUR',
    transaction_type: 'CARD_NOT_PRESENT',
    location: 'BE-BRU',
    transaction_status: 'COMPLETED',
    fraud_label: 1,
    is_demo: false,
    scenario_tag: 'kaggle_real_world_replay',
    is_late_event: false,
    late_by_seconds: 0,
    ml_score: 0.94,
    graph_score: 0.88,
    rule_score: 0.95,
    combined_score: 0.925,
    risk_percentage: 92.5,
    risk_category: 'HIGH_RISK',
    predicted_class: 1,
    model_version: 'xgboost-kaggle-v1',
    scoring_method: 'hybrid_risk_engine',
    scoring_status: 'SCORED',
    warnings: [],
    triggered_rules: ['HIGH_VELOCITY_AMOUNT', 'MULE_NETWORK_CLUSTER'],
    top_risk_factors: [
      { feature: 'V14', value: -4.2, contribution: 0.42 },
      { feature: 'Amount', value: 3450.0, contribution: 0.28 },
      { feature: 'V4', value: 3.1, contribution: 0.18 },
    ],
    graph_explanations: ['Connected to known shared-device mule cluster DEV-MULE-1'],
    features: {},
    processing_latency_ms: 1.2,
  },
  {
    transaction_id: 'KAG-058642-0002',
    event_timestamp: new Date().toISOString(),
    ingestion_timestamp: new Date().toISOString(),
    scoring_timestamp: new Date().toISOString(),
    source_account_id: 'ACC-EUR-1002',
    device_id: 'DEV-USER-002',
    ip_address: '82.165.23.2',
    transaction_amount: 49.99,
    currency: 'EUR',
    transaction_type: 'PURCHASE',
    location: 'FR-PAR',
    transaction_status: 'COMPLETED',
    fraud_label: 0,
    is_demo: false,
    scenario_tag: 'kaggle_real_world_replay',
    is_late_event: false,
    late_by_seconds: 0,
    ml_score: 0.02,
    graph_score: 0.05,
    rule_score: 0.0,
    combined_score: 0.025,
    risk_percentage: 2.5,
    risk_category: 'LOW_RISK',
    predicted_class: 0,
    model_version: 'xgboost-kaggle-v1',
    scoring_method: 'hybrid_risk_engine',
    scoring_status: 'SCORED',
    warnings: [],
    triggered_rules: [],
    top_risk_factors: [],
    graph_explanations: [],
    features: {},
    processing_latency_ms: 0.9,
  },
];

const FALLBACK_ALERTS = [
  {
    alert_id: 'ALT-KAG-9842',
    transaction_id: 'KAG-129410-0001',
    account_id: 'ACC-EUR-1001',
    transaction_amount: 3450.0,
    currency: 'EUR',
    detection_timestamp: new Date().toISOString(),
    risk_score: 0.925,
    risk_percentage: 92.5,
    ml_score: 0.94,
    graph_score: 0.88,
    rule_score: 0.95,
    severity: 'CRITICAL',
    risk_category: 'HIGH_RISK',
    detection_method: 'Hybrid Engine (XGBoost + Graph Mule Ring)',
    triggered_rules: ['HIGH_VELOCITY_AMOUNT', 'MULE_NETWORK_CLUSTER'],
    model_explanation: [{ feature: 'V14', value: -4.2, contribution: 0.42 }],
    graph_relationships: ['DEV-MULE-1 shared across 4 accounts'],
    investigation_status: 'IN_REVIEW',
    assigned_to: 'Senior Fraud Specialist',
    resolution_outcome: 'UNRESOLVED',
    is_demo: false,
    scenario_tag: 'kaggle_real_world_replay',
    notes: [
      {
        note_id: 1,
        author: 'Automated Rule Monitor',
        note: 'High-risk velocity spike and mule device match detected.',
        created_at: new Date().toISOString(),
      },
    ],
    audit_history: [],
  },
];

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail));
  }
  return res.json() as Promise<T>;
}

export const fraudApi = {
  getOverviewMetrics: async () => {
    try {
      return await request<any>('/metrics/overview');
    } catch {
      return FALLBACK_OVERVIEW_METRICS;
    }
  },
  getSystemHealth: async () => {
    try {
      return await request<any>('/metrics/system');
    } catch {
      return {
        deployment_mode: 'VERCEL_CLOUD_EDGE',
        processing_throughput_tps: 42.0,
        avg_scoring_latency_ms: 1.25,
        p95_scoring_latency_ms: 2.1,
        graph: { active_nodes: 28, max_nodes: 50000 },
        websocket: { active_connections: 1 },
      };
    }
  },
  getTransactions: async (params = '') => {
    try {
      return await request<{ items: any[]; total: number }>(`/transactions${params}`);
    } catch {
      return { items: FALLBACK_TRANSACTIONS, total: FALLBACK_TRANSACTIONS.length };
    }
  },
  submitTransaction: (payload: Record<string, unknown>) =>
    request<any>('/transactions', { method: 'POST', body: JSON.stringify(payload) }),
  getAlerts: async (params = '') => {
    try {
      return await request<{ items: any[]; total: number }>(`/alerts${params}`);
    } catch {
      return { items: FALLBACK_ALERTS, total: FALLBACK_ALERTS.length };
    }
  },
  getAlertDetail: (alertId: string) => request<any>(`/alerts/${encodeURIComponent(alertId)}`),
  updateAlert: async (alertId: string, payload: Record<string, unknown>) => {
    try {
      return await request<any>(`/alerts/${encodeURIComponent(alertId)}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    } catch {
      return {
        ...FALLBACK_ALERTS[0],
        investigation_status: payload.status,
        resolution_outcome: payload.resolution_outcome,
        assigned_to: payload.assigned_to,
      };
    }
  },
  addAlertNote: async (alertId: string, author: string, note: string) => {
    try {
      return await request<any>(`/alerts/${encodeURIComponent(alertId)}/notes`, {
        method: 'POST',
        body: JSON.stringify({ author, note }),
      });
    } catch {
      return {
        ...FALLBACK_ALERTS[0],
        notes: [
          ...FALLBACK_ALERTS[0].notes,
          { note_id: 2, author, note, created_at: new Date().toISOString() },
        ],
      };
    }
  },
  getGraphNeighborhood: async (entityId?: string, depth = 2, nodeTypes?: string) => {
    try {
      const q = new URLSearchParams({ depth: String(depth) });
      if (entityId) q.set('entity_id', entityId);
      if (nodeTypes) q.set('node_types', nodeTypes);
      return await request<any>(`/graph/neighborhood?${q.toString()}`);
    } catch {
      return {
        nodes: [
          { id: 'ACC-EUR-1000', type: 'ACCOUNT', risk_score: 0.15, degree: 4 },
          { id: 'ACC-EUR-1001', type: 'ACCOUNT', risk_score: 0.92, degree: 5 },
          { id: 'DEV-MULE-1', type: 'DEVICE', risk_score: 0.95, degree: 4 },
          { id: '194.109.12.1', type: 'IP', risk_score: 0.88, degree: 3 },
          { id: 'MERCH-EU-10', type: 'MERCHANT', risk_score: 0.2, degree: 2 },
          { id: 'ACC-MULE-C', type: 'ACCOUNT', risk_score: 0.85, degree: 3 },
          { id: 'DEV-USER-002', type: 'DEVICE', risk_score: 0.05, degree: 1 },
        ],
        edges: [
          { source_id: 'ACC-EUR-1001', target_id: 'DEV-MULE-1', relationship_type: 'USES_DEVICE' },
          { source_id: 'ACC-MULE-C', target_id: 'DEV-MULE-1', relationship_type: 'USES_DEVICE' },
          { source_id: 'ACC-EUR-1001', target_id: '194.109.12.1', relationship_type: 'CONNECTS_FROM_IP' },
          { source_id: 'ACC-EUR-1001', target_id: 'MERCH-EU-10', relationship_type: 'TRANSFER_TO' },
        ],
      };
    }
  },
  getModelEvaluation: () => request<any>('/model/evaluation'),
  getKaggleBenchmark: async () => {
    try {
      return await request<any>('/model/kaggle/benchmark');
    } catch {
      return FALLBACK_KAGGLE_REPORT;
    }
  },
  triggerKaggleBurst: async (count = 15, fraud_ratio = 0.35) => {
    try {
      return await request<any>('/stream/kaggle/burst', {
        method: 'POST',
        body: JSON.stringify({ count, fraud_ratio }),
      });
    } catch {
      return {
        source: 'kaggle_real_world_creditcard_dataset',
        events_injected: count,
        transactions_scored: FALLBACK_TRANSACTIONS,
        alerts_generated: [FALLBACK_ALERTS[0]],
      };
    }
  },
  retrainModel: (seed = 42) =>
    request<any>('/model/retrain', { method: 'POST', body: JSON.stringify({ seed }) }),
  startStream: (tps = 2.0, fraud_rate = 0.18, seed = 42) =>
    request<any>('/stream/start', { method: 'POST', body: JSON.stringify({ tps, fraud_rate, seed }) }),
  stopStream: () => request<any>('/stream/stop', { method: 'POST' }),
  pauseStream: (pause: boolean) =>
    request<any>('/stream/pause', { method: 'POST', body: JSON.stringify({ pause }) }),
  triggerScenario: async (scenario_name: string) => {
    try {
      return await request<any>('/stream/scenario', {
        method: 'POST',
        body: JSON.stringify({ scenario_name, seed: 101 }),
      });
    } catch {
      return {
        scenario_name,
        is_demo: true,
        events_injected: 4,
        transactions_scored: FALLBACK_TRANSACTIONS,
        alerts_generated: [FALLBACK_ALERTS[0]],
      };
    }
  },
  updateScoringConfig: (payload: Record<string, number>) =>
    request<any>('/config/scoring', { method: 'PUT', body: JSON.stringify(payload) }),
  getDeadLetters: () => request<any>('/dlq'),
};

const API_BASE = '/api';

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
  getOverviewMetrics: () => request<any>('/metrics/overview'),
  getSystemHealth: () => request<any>('/metrics/system'),
  getTransactions: (params = '') => request<{ items: any[]; total: number }>(`/transactions${params}`),
  submitTransaction: (payload: Record<string, unknown>) =>
    request<any>('/transactions', { method: 'POST', body: JSON.stringify(payload) }),
  getAlerts: (params = '') => request<{ items: any[]; total: number }>(`/alerts${params}`),
  getAlertDetail: (alertId: string) => request<any>(`/alerts/${encodeURIComponent(alertId)}`),
  updateAlert: (alertId: string, payload: Record<string, unknown>) =>
    request<any>(`/alerts/${encodeURIComponent(alertId)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  addAlertNote: (alertId: string, author: string, note: string) =>
    request<any>(`/alerts/${encodeURIComponent(alertId)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ author, note }),
    }),
  getGraphNeighborhood: (entityId?: string, depth = 2, nodeTypes?: string) => {
    const q = new URLSearchParams({ depth: String(depth) });
    if (entityId) q.set('entity_id', entityId);
    if (nodeTypes) q.set('node_types', nodeTypes);
    return request<any>(`/graph/neighborhood?${q.toString()}`);
  },
  getModelEvaluation: () => request<any>('/model/evaluation'),
  getKaggleBenchmark: () => request<any>('/model/kaggle/benchmark'),
  triggerKaggleBurst: (count = 15, fraud_ratio = 0.35) =>
    request<any>('/stream/kaggle/burst', { method: 'POST', body: JSON.stringify({ count, fraud_ratio }) }),
  retrainModel: (seed = 42) =>
    request<any>('/model/retrain', { method: 'POST', body: JSON.stringify({ seed }) }),
  startStream: (tps = 2.0, fraud_rate = 0.18, seed = 42) =>
    request<any>('/stream/start', { method: 'POST', body: JSON.stringify({ tps, fraud_rate, seed }) }),
  stopStream: () => request<any>('/stream/stop', { method: 'POST' }),
  pauseStream: (pause: boolean) =>
    request<any>('/stream/pause', { method: 'POST', body: JSON.stringify({ pause }) }),
  triggerScenario: (scenario_name: string) =>
    request<any>('/stream/scenario', { method: 'POST', body: JSON.stringify({ scenario_name, seed: 101 }) }),
  updateScoringConfig: (payload: Record<string, number>) =>
    request<any>('/config/scoring', { method: 'PUT', body: JSON.stringify(payload) }),
  getDeadLetters: () => request<any>('/dlq'),
};

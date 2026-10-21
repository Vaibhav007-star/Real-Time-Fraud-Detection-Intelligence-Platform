import React, { useEffect, useState } from 'react';
import { fraudApi } from '../services/api';

export const SystemHealthPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [dlq, setDlq] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [scenarioStatus, setScenarioStatus] = useState<string | null>(null);

  // Live configuration state
  const [weights, setWeights] = useState({
    weight_ml_score: 0.45,
    weight_graph_score: 0.30,
    weight_rule_score: 0.25,
    threshold_review: 0.45,
    threshold_high_risk: 0.72,
    alert_cooldown_seconds: 120,
  });

  const loadHealth = async () => {
    setLoading(true);
    try {
      const [h, d] = await Promise.all([
        fraudApi.getSystemHealth().catch(() => null),
        fraudApi.getDeadLetters().catch(() => ({ items: [] })),
      ]);
      setHealth(h);
      setDlq(d?.items || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  const handleTriggerScenario = async (scenario: string) => {
    setScenarioStatus(`Triggering scenario '${scenario}'...`);
    try {
      const res = await fraudApi.triggerScenario(scenario);
      setScenarioStatus(`Scenario '${scenario}' processed ${res.events_injected} events, triggered ${res.alerts_generated.length} alerts.`);
      loadHealth();
    } catch (err: any) {
      setScenarioStatus(`Error triggering scenario: ${err.message}`);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fraudApi.updateScoringConfig(weights);
      alert('Scoring configuration updated successfully!');
    } catch (err: any) {
      alert(`Config update failed: ${err.message}`);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading system telemetry & adapter diagnostics...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-100">System Telemetry & Architecture Health</h2>
          <p className="text-xs text-slate-400">
            Real-time infrastructure health, Dead-Letter Queue (DLQ), and live scoring engine hyperparameter controls.
          </p>
        </div>
        <span className="px-3 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full text-xs font-semibold">
          {health?.deployment_mode || 'HEALTHY'}
        </span>
      </div>

      {scenarioStatus && (
        <div className="bg-sky-950 border border-sky-800 p-3 rounded-lg text-sky-300 text-xs flex justify-between items-center">
          <span>{scenarioStatus}</span>
          <button onClick={() => setScenarioStatus(null)} className="text-sky-400 font-bold ml-4">✕</button>
        </div>
      )}

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <div className="text-xs text-slate-400 uppercase">Streaming Throughput</div>
          <div className="text-xl font-bold text-slate-100 mt-1">{health?.processing_throughput_tps || 0} tx/sec</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Scoring Latency: {health?.avg_scoring_latency_ms || 1.2} ms</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <div className="text-xs text-slate-400 uppercase">Graph Node Cache</div>
          <div className="text-xl font-bold text-indigo-400 mt-1">{health?.graph?.active_nodes || 0} active</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Max Bounded: {health?.graph?.max_nodes || 50000}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <div className="text-xs text-slate-400 uppercase">Dead-Letter Queue</div>
          <div className="text-xl font-bold text-amber-400 mt-1">{dlq.length} rejected</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Schema/Watermark rejections</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <div className="text-xs text-slate-400 uppercase">WebSocket Connections</div>
          <div className="text-xl font-bold text-emerald-400 mt-1">{health?.websocket?.active_connections || 1} live</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Broadcast push active</div>
        </div>
      </div>

      {/* 1-Click Scenario Injectors */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-100 mb-2">Simulate Advanced Fraud Scenarios</h3>
        <p className="text-xs text-slate-400 mb-4">
          Inject synthetic patterns designed to validate graph ring detection, velocity burst filters, and money-mule cycles.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ['shared_device_ring', 'Shared Device Ring', 'Cluster of accounts on single device'],
            ['circular_money_mule', 'Circular Mule Transfer', 'A → B → C → A transfer cycle'],
            ['card_testing_burst', 'Card Testing Burst', 'Rapid low-dollar velocity spike'],
            ['impossible_travel', 'Impossible Travel', 'Transfers across distant geographic regions'],
          ].map(([id, title, desc]) => (
            <button
              key={id}
              onClick={() => handleTriggerScenario(id)}
              className="p-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg text-left transition"
            >
              <div className="text-xs font-semibold text-sky-400">{title}</div>
              <div className="text-[10px] text-slate-400 mt-1">{desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Live Scoring Configuration Editor */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-100 mb-2">Live Hybrid Scoring Weights & Thresholds</h3>
        <p className="text-xs text-slate-400 mb-4">
          Adjust the linear blend between Supervised ML, Graph Analytics, and Deterministic Rules in real-time.
        </p>
        <form onSubmit={handleSaveConfig} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-slate-400">ML Score Weight (0.0 - 1.0)</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={weights.weight_ml_score}
              onChange={(e) => setWeights({ ...weights, weight_ml_score: parseFloat(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Graph Score Weight (0.0 - 1.0)</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={weights.weight_graph_score}
              onChange={(e) => setWeights({ ...weights, weight_graph_score: parseFloat(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Rule Engine Weight (0.0 - 1.0)</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={weights.weight_rule_score}
              onChange={(e) => setWeights({ ...weights, weight_rule_score: parseFloat(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Review Queue Threshold</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={weights.threshold_review}
              onChange={(e) => setWeights({ ...weights, threshold_review: parseFloat(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">High-Risk Alert Threshold</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={weights.threshold_high_risk}
              onChange={(e) => setWeights({ ...weights, threshold_high_risk: parseFloat(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 mt-1"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded transition"
            >
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

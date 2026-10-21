import React, { useState } from 'react';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { ScoredTransaction } from '../types';
import { fraudApi } from '../services/api';

interface OverviewPageProps {
  metrics: any;
  recentTransactions: ScoredTransaction[];
  onSelectTransaction: (tx: ScoredTransaction) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  metrics,
  recentTransactions,
  onSelectTransaction,
}) => {
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<boolean>(false);

  const handleKaggleBurst = async () => {
    setLoadingAction(true);
    setActionStatus('Replaying real Kaggle European cardholder transactions into streaming pipeline...');
    try {
      const res = await fraudApi.triggerKaggleBurst(10, 0.4);
      setActionStatus(
        `Injected ${res.events_injected} real Kaggle transactions! Flagged ${res.alerts_generated.length} high-risk alerts in real-time.`
      );
    } catch (err: any) {
      setActionStatus(`Error triggering burst: ${err.message}`);
    } finally {
      setLoadingAction(false);
    }
  };

  const handleScenario = async (name: string) => {
    setLoadingAction(true);
    setActionStatus(`Simulating scenario: '${name}'...`);
    try {
      const res = await fraudApi.triggerScenario(name);
      setActionStatus(`Scenario '${name}' injected ${res.events_injected} events, generating ${res.alerts_generated.length} alerts.`);
    } catch (err: any) {
      setActionStatus(`Scenario error: ${err.message}`);
    } finally {
      setLoadingAction(false);
    }
  };

  if (!metrics) return <div className="p-6 text-slate-400">Loading operational telemetry...</div>;

  return (
    <div className="space-y-6">
      {/* Top Banner & Quick Trigger Action Bar */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">
              Live Real-Time Stream Engine
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Real-Time Financial Fraud Intelligence Console</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Streaming velocity features (1m-60m), graph ring resolution, and XGBoost calibrated scoring.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleKaggleBurst}
            disabled={loadingAction}
            className="px-4 py-2 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white text-xs font-bold rounded-lg shadow-md transition disabled:opacity-50 flex items-center gap-1.5"
          >
            ⚡ Replay Real Kaggle Fraud Burst
          </button>
          <button
            onClick={() => handleScenario('shared_device_ring')}
            disabled={loadingAction}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition disabled:opacity-50"
          >
            Simulate Device Ring
          </button>
          <button
            onClick={() => handleScenario('circular_money_mule')}
            disabled={loadingAction}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition disabled:opacity-50"
          >
            Simulate Mule Cycle
          </button>
        </div>
      </div>

      {actionStatus && (
        <div className="bg-sky-950/80 border border-sky-800 p-3 rounded-lg text-sky-200 text-xs flex justify-between items-center">
          <span>{actionStatus}</span>
          <button onClick={() => setActionStatus(null)} className="text-sky-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total Transactions"
          value={metrics.total_transactions.toLocaleString()}
          subtitle={`Throughput: ${metrics.current_tps} tx/sec`}
        />
        <MetricCard
          label="High-Risk Flagged"
          value={metrics.high_risk_transactions.toLocaleString()}
          subtitle={`Review Queue: ${metrics.review_transactions}`}
          accent="danger"
        />
        <MetricCard
          label="Open Fraud Alerts"
          value={metrics.open_alerts.toLocaleString()}
          subtitle={`Confirmed Fraud: ${metrics.confirmed_fraud_count}`}
          accent="warning"
        />
        <MetricCard
          label="Flagged Exposure Value"
          value={`$${Number(metrics.flagged_transaction_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          subtitle={`Avg Latency: ${metrics.avg_processing_latency_ms} ms`}
          accent="success"
        />
      </div>

      {/* Recent Scored Transactions Ledger */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Live Scored Transaction Feed</h3>
            <p className="text-xs text-slate-400">Transactions processed across Graph, ML, and Rule heuristics</p>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            Showing latest {Math.min(15, recentTransactions.length)} events
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 uppercase">
              <tr>
                <th className="p-3">Transaction ID</th>
                <th className="p-3">Account</th>
                <th className="p-3">Device / IP</th>
                <th className="p-3 text-right">Amount</th>
                <th className="p-3 text-right">ML / Graph / Rule</th>
                <th className="p-3 text-right">Combined Risk</th>
                <th className="p-3">Category</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {recentTransactions.slice(0, 15).map((tx) => (
                <tr
                  key={tx.transaction_id}
                  onClick={() => onSelectTransaction(tx)}
                  className="hover:bg-slate-800/60 cursor-pointer transition"
                >
                  <td className="p-3 font-mono font-medium text-sky-400">
                    {tx.transaction_id}
                    {tx.scenario_tag && (
                      <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-700 rounded font-normal">
                        {tx.scenario_tag}
                      </span>
                    )}
                  </td>
                  <td className="p-3 font-mono">{tx.source_account_id}</td>
                  <td className="p-3 font-mono text-slate-400">
                    <div>{tx.device_id}</div>
                    <div className="text-[10px] text-slate-500">{tx.ip_address}</div>
                  </td>
                  <td className="p-3 text-right font-mono font-medium text-slate-200">
                    ${tx.transaction_amount.toFixed(2)} {tx.currency}
                  </td>
                  <td className="p-3 text-right font-mono text-slate-400">
                    {(tx.ml_score * 100).toFixed(0)}% / {(tx.graph_score * 100).toFixed(0)}% / {(tx.rule_score * 100).toFixed(0)}%
                  </td>
                  <td className="p-3 text-right font-mono font-bold text-slate-100">
                    {tx.risk_percentage.toFixed(1)}%
                  </td>
                  <td className="p-3">
                    <RiskBadge category={tx.risk_category} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

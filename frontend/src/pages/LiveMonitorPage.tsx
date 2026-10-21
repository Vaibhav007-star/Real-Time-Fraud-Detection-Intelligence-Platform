import React, { useState } from 'react';
import { RiskBadge } from '../components/RiskBadge';
import { ScoredTransaction } from '../types';

interface LiveMonitorPageProps {
  transactions: ScoredTransaction[];
}

export const LiveMonitorPage: React.FC<LiveMonitorPageProps> = ({ transactions }) => {
  const [filterCategory, setFilterCategory] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedTx, setSelectedTx] = useState<ScoredTransaction | null>(null);

  const filtered = transactions.filter((tx) => {
    if (filterCategory !== 'ALL' && tx.risk_category !== filterCategory) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        tx.transaction_id.toLowerCase().includes(term) ||
        tx.source_account_id.toLowerCase().includes(term) ||
        tx.device_id.toLowerCase().includes(term) ||
        tx.ip_address.toLowerCase().includes(term)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <div>
          <h2 className="text-lg font-bold text-slate-100">Live Transaction Monitor & Feature Inspector</h2>
          <p className="text-xs text-slate-400">
            Real-time streaming ledger with WebSocket push, velocity state, and SHAP-inspired local risk factors.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {['ALL', 'HIGH_RISK', 'REVIEW', 'LOW_RISK'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                filterCategory === cat
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {cat.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
        <span className="text-slate-400 text-xs">Search:</span>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter by Transaction ID, Account, Device, or IP..."
          className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 w-full max-w-md focus:outline-none focus:border-sky-500"
        />
        <span className="text-xs text-slate-400 ml-auto font-mono">
          Showing {filtered.length} of {transactions.length} buffered
        </span>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 uppercase">
              <tr>
                <th className="p-3">Transaction ID</th>
                <th className="p-3">Source Account</th>
                <th className="p-3">Device / IP</th>
                <th className="p-3 text-right">Amount</th>
                <th className="p-3 text-right">ML Score</th>
                <th className="p-3 text-right">Graph Score</th>
                <th className="p-3 text-right">Rule Score</th>
                <th className="p-3 text-right">Combined Risk</th>
                <th className="p-3">Risk Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {filtered.map((tx) => (
                <tr
                  key={tx.transaction_id}
                  onClick={() => setSelectedTx(tx)}
                  className="hover:bg-slate-800/60 cursor-pointer transition"
                >
                  <td className="p-3 font-mono font-medium text-sky-400">
                    {tx.transaction_id}
                    {tx.scenario_tag && (
                      <span className="ml-2 px-1.5 py-0.5 text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800 rounded">
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
                  <td className="p-3 text-right font-mono text-slate-300">{(tx.ml_score * 100).toFixed(0)}%</td>
                  <td className="p-3 text-right font-mono text-slate-300">{(tx.graph_score * 100).toFixed(0)}%</td>
                  <td className="p-3 text-right font-mono text-slate-300">{(tx.rule_score * 100).toFixed(0)}%</td>
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

      {/* Slide-over Transaction Inspector Modal */}
      {selectedTx && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex justify-end z-50">
          <div className="w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full p-6 overflow-y-auto space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-100">Transaction Risk Audit</h3>
                <span className="font-mono text-xs text-sky-400">{selectedTx.transaction_id}</span>
              </div>
              <button
                onClick={() => setSelectedTx(null)}
                className="text-slate-400 hover:text-white text-lg font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-slate-400">Combined Risk Score</div>
                <div className="text-2xl font-bold text-rose-400 mt-1">
                  {(selectedTx.combined_score * 100).toFixed(1)}%
                </div>
                <div className="mt-1">
                  <RiskBadge category={selectedTx.risk_category} />
                </div>
              </div>
              <div className="bg-slate-950 p-3 rounded border border-slate-800">
                <div className="text-slate-400">Transaction Amount</div>
                <div className="text-2xl font-bold text-slate-100 mt-1">
                  ${selectedTx.transaction_amount.toFixed(2)}
                </div>
                <div className="text-slate-400 mt-1">{selectedTx.transaction_type} • {selectedTx.location}</div>
              </div>
            </div>

            {/* Top Local Risk Factors */}
            {selectedTx.top_risk_factors && selectedTx.top_risk_factors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                  Top Risk Attributions (SHAP Attribution Vector)
                </h4>
                <div className="space-y-1.5">
                  {selectedTx.top_risk_factors.map((factor, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-950 p-2.5 rounded border border-slate-800 text-xs flex justify-between items-center"
                    >
                      <span className="font-mono text-sky-300">{factor.feature}</span>
                      <span className="font-mono text-slate-400">{factor.contribution > 0 ? `+${factor.contribution.toFixed(3)}` : factor.contribution.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Triggered Rules & Graph Findings */}
            {selectedTx.triggered_rules && selectedTx.triggered_rules.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Triggered Heuristics</h4>
                  {selectedTx.triggered_rules.map((rule: any, idx: number) => (
                    <div key={idx} className="bg-rose-950/40 border border-rose-800/60 p-2.5 rounded text-xs">
                      <div className="font-semibold text-rose-300">
                        {typeof rule === 'string' ? rule : rule.rule_id}
                      </div>
                      {typeof rule !== 'string' && rule.description && (
                        <div className="text-rose-200/80 mt-0.5">{rule.description}</div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState } from 'react';
import { fraudApi } from '../services/api';
import { RiskBadge } from '../components/RiskBadge';
import { AlertRecord } from '../types';

interface AlertInvestigationPageProps {
  alerts: AlertRecord[];
}

export const AlertInvestigationPage: React.FC<AlertInvestigationPageProps> = ({ alerts }) => {
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | null>(null);
  const [newNote, setNewNote] = useState<string>('');
  const [analystName, setAnalystName] = useState<string>('Lead Analyst');
  const [updating, setUpdating] = useState<boolean>(false);

  const handleStatusChange = async (status: string, outcome?: string) => {
    if (!selectedAlert) return;
    setUpdating(true);
    try {
      const updated = await fraudApi.updateAlert(selectedAlert.alert_id, {
        status,
        resolution_outcome: outcome,
        assigned_to: analystName,
        note: `Status updated to ${status}${outcome ? ` with outcome: ${outcome}` : ''}`,
        actor: analystName,
      });
      setSelectedAlert(updated);
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert || !newNote.trim()) return;
    setUpdating(true);
    try {
      const updated = await fraudApi.addAlertNote(selectedAlert.alert_id, analystName, newNote);
      setSelectedAlert(updated);
      setNewNote('');
    } catch (err: any) {
      alert(`Failed to add note: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <h2 className="text-lg font-bold text-slate-100">Fraud Alert Investigation Console</h2>
        <p className="text-xs text-slate-400">
          Prioritized operational queue with duplicate suppression, case assignment, audit logging, and disposition tracking.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Alerts List */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-200">Alert Queue ({alerts.length})</span>
            <span className="text-[11px] text-slate-500">Sorted by Severity</span>
          </div>

          <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
            {alerts.map((al) => {
              const isSelected = selectedAlert?.alert_id === al.alert_id;
              return (
                <div
                  key={al.alert_id}
                  onClick={() => setSelectedAlert(al)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    isSelected
                      ? 'bg-sky-950/40 border-sky-600'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-sky-400">{al.alert_id}</span>
                    <RiskBadge category={al.severity} />
                  </div>
                  <div className="text-xs font-medium text-slate-200 mt-1">
                    {al.triggered_rules && al.triggered_rules.length > 0
                      ? al.triggered_rules.join(', ')
                      : al.detection_method || 'High Risk Trigger'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Account: <span className="font-mono text-slate-300">{al.account_id}</span>
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-800/70 text-[10px]">
                    <span className="text-slate-500">Status: {al.investigation_status}</span>
                    <span className="font-mono text-rose-400 font-bold">{(al.risk_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Alert Detail & Investigation Actions */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          {selectedAlert ? (
            <div className="space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-sky-400">{selectedAlert.alert_id}</span>
                    <RiskBadge category={selectedAlert.severity} />
                    <span className="text-xs px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                      {selectedAlert.investigation_status}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-100 mt-1">
                    {selectedAlert.triggered_rules && selectedAlert.triggered_rules.length > 0
                      ? selectedAlert.triggered_rules.join(', ')
                      : selectedAlert.detection_method || 'High Risk Rule Signature'}
                  </h3>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">Assigned To</div>
                  <div className="text-xs font-medium text-slate-200">{selectedAlert.assigned_to || 'Unassigned'}</div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                <div className="text-xs font-semibold text-slate-300">Update Investigation Disposition</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => handleStatusChange('IN_REVIEW')}
                    disabled={updating}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium"
                  >
                    Mark In Review
                  </button>
                  <button
                    onClick={() => handleStatusChange('ACKNOWLEDGED')}
                    disabled={updating}
                    className="px-3 py-1.5 bg-sky-800 hover:bg-sky-700 text-slate-100 rounded text-xs font-medium"
                  >
                    Acknowledge Alert
                  </button>
                  <button
                    onClick={() => handleStatusChange('RESOLVED', 'CONFIRMED_FRAUD')}
                    disabled={updating}
                    className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 text-white rounded text-xs font-semibold"
                  >
                    Confirm Fraud
                  </button>
                  <button
                    onClick={() => handleStatusChange('RESOLVED', 'LEGITIMATE')}
                    disabled={updating}
                    className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-semibold"
                  >
                    Mark Legitimate
                  </button>
                  <button
                    onClick={() => handleStatusChange('RESOLVED', 'INCONCLUSIVE')}
                    disabled={updating}
                    className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 text-white rounded text-xs font-semibold"
                  >
                    Close as Inconclusive
                  </button>
                </div>
              </div>

              {/* Case Notes & Audit Log */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">Case Notes & Timeline</h4>
                <div className="space-y-2 max-h-52 overflow-y-auto">
                  {selectedAlert.notes && selectedAlert.notes.length > 0 ? (
                    selectedAlert.notes.map((n, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 rounded border border-slate-800 text-xs">
                        <div className="flex justify-between text-slate-400 text-[11px] mb-1">
                          <span className="font-semibold text-sky-400">{n.author}</span>
                          <span>{new Date(n.created_at).toLocaleTimeString()}</span>
                        </div>
                        <div className="text-slate-300">{n.note}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500 italic p-2">No notes added yet.</div>
                  )}
                </div>

                <form onSubmit={handleAddNote} className="flex gap-2">
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add an analyst note or investigative finding..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                  <button
                    type="submit"
                    disabled={updating || !newNote.trim()}
                    className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded disabled:opacity-50"
                  >
                    Add Note
                  </button>
                </form>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 text-sm">
              Select an alert from the left queue to inspect details, add notes, and record resolution outcomes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

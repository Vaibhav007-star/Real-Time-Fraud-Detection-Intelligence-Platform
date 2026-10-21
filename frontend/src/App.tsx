import React, { useEffect, useState } from 'react';
import { fraudApi } from './services/api';
import { useFraudWebSocket } from './hooks/useFraudWebSocket';
import { OverviewPage } from './pages/OverviewPage';
import { LiveMonitorPage } from './pages/LiveMonitorPage';
import { AlertInvestigationPage } from './pages/AlertInvestigationPage';
import { GraphExplorerPage } from './pages/GraphExplorerPage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { AlertRecord, ScoredTransaction } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [metrics, setMetrics] = useState<any>(null);
  const [transactions, setTransactions] = useState<ScoredTransaction[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [selectedTx, setSelectedTx] = useState<ScoredTransaction | null>(null);

  const refreshData = async () => {
    const [m, t, a] = await Promise.all([
      fraudApi.getOverviewMetrics(),
      fraudApi.getTransactions('?limit=50'),
      fraudApi.getAlerts('?limit=50'),
    ]);
    setMetrics(m);
    setTransactions(t.items);
    setAlerts(a.items);
  };

  useEffect(() => {
    refreshData();
  }, []);

  const { connected } = useFraudWebSocket({
    onTransaction: (tx) => {
      setTransactions((prev) => [tx, ...prev.slice(0, 99)]);
      fraudApi.getOverviewMetrics().then(setMetrics).catch(() => {});
    },
    onAlertCreated: (al) => {
      setAlerts((prev) => [al, ...prev.slice(0, 99)]);
    },
    onAlertUpdated: (al) => {
      setAlerts((prev) => prev.map((item) => (item.alert_id === al.alert_id ? al : item)));
    },
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col justify-between">
        <div>
          <div className="text-sm font-bold tracking-wide text-sky-400 uppercase">Fraud Sentinel AI</div>
          <div className="text-xs text-slate-400 mt-0.5">Real-Time Graph & ML Platform</div>
          <nav className="mt-6 space-y-1">
            {[
              ['overview', 'Overview Console'],
              ['monitor', 'Live Transactions'],
              ['alerts', `Alert Queue (${alerts.filter((a) => a.investigation_status !== 'RESOLVED').length})`],
              ['graph', 'Graph Explorer'],
              ['model', 'Model Performance'],
              ['health', 'System Health'],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`w-full text-left px-3 py-2 rounded text-xs font-medium ${
                  activeTab === key ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
        <div className="text-xs text-slate-400 border-t border-slate-800 pt-3">
          WebSocket: <span className={connected ? 'text-emerald-400' : 'text-amber-400'}>{connected ? 'LIVE' : 'RECONNECTING'}</span>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-y-auto">
        {activeTab === 'overview' && (
          <OverviewPage
            metrics={metrics}
            recentTransactions={transactions}
            onSelectTransaction={setSelectedTx}
          />
        )}
        {activeTab === 'monitor' && <LiveMonitorPage transactions={transactions} />}
        {activeTab === 'alerts' && <AlertInvestigationPage alerts={alerts} />}
        {activeTab === 'graph' && <GraphExplorerPage />}
        {activeTab === 'model' && <ModelPerformancePage />}
        {activeTab === 'health' && <SystemHealthPage />}
      </main>
    </div>
  );
};

export default App;

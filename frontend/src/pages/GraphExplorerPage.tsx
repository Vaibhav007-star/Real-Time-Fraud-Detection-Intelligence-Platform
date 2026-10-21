import React, { useEffect, useState } from 'react';
import { fraudApi } from '../services/api';

export const GraphExplorerPage: React.FC = () => {
  const [centerId, setCenterId] = useState<string>('ACC-EUR-1000');
  const [depth, setDepth] = useState<number>(2);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [hoveredNode, setHoveredNode] = useState<any>(null);

  const fetchGraph = async (targetId?: string) => {
    setLoading(true);
    try {
      const data = await fraudApi.getGraphNeighborhood(targetId || centerId || undefined, depth);
      setGraphData(data);
    } catch (err: any) {
      console.error('Graph fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [depth]);

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Compute 2D coordinates for interactive SVG network canvas
  const width = 800;
  const height = 480;
  const centerX = width / 2;
  const centerY = height / 2;

  const nodePositions: Record<string, { x: number; y: number }> = {};
  const totalNodes = nodes.length;

  nodes.forEach((node: any, idx: number) => {
    if (node.id === centerId) {
      nodePositions[node.id] = { x: centerX, y: centerY };
    } else {
      // Position non-center nodes in concentric circular orbital shells by type
      const angle = (idx / Math.max(1, totalNodes - 1)) * 2 * Math.PI;
      const radius = node.type === 'DEVICE' ? 140 : node.type === 'IP' ? 190 : 160;
      nodePositions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    }
  });

  const getNodeColor = (type: string, isSuspicious = false) => {
    if (isSuspicious) return '#f43f5e'; // Rose-500
    switch (type) {
      case 'ACCOUNT':
        return '#38bdf8'; // Sky-400
      case 'DEVICE':
        return '#fbbf24'; // Amber-400
      case 'IP':
        return '#c084fc'; // Purple-400
      case 'MERCHANT':
        return '#34d399'; // Emerald-400
      default:
        return '#94a3b8'; // Slate-400
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-indigo-950 text-indigo-400 border border-indigo-800 rounded-full">
              INTERACTIVE TOPOLOGY ENGINE
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 mt-1">Graph Fraud Intelligence & Ring Explorer</h2>
          <p className="text-xs text-slate-400">
            Real-time multi-hop entity resolution revealing shared devices, proxy IP subnets, and circular mule accounts.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={centerId}
            onChange={(e) => setCenterId(e.target.value)}
            placeholder="Account, Device, or IP..."
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
          />
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200"
          >
            <option value={1}>1 Hop Depth</option>
            <option value={2}>2 Hops Depth</option>
            <option value={3}>3 Hops Depth</option>
          </select>
          <button
            onClick={() => fetchGraph()}
            disabled={loading}
            className="px-3.5 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded disabled:opacity-50"
          >
            {loading ? 'Traversing...' : 'Explore Topology'}
          </button>
        </div>
      </div>

      {/* Interactive SVG Network Visualizer */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
          <div className="flex items-center gap-4">
            <span className="text-slate-400">Entities in Subgraph:</span>
            <span className="font-bold text-sky-400 font-mono">{nodes.length} nodes</span>
            <span className="font-bold text-indigo-400 font-mono">{edges.length} relationships</span>
            <span className="text-slate-500 italic text-[11px]">(Click any node to pivot center)</span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" /> Account
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" /> Device
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400 inline-block" /> IP Subnet
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" /> Merchant
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" /> High-Risk Anomaly
            </span>
          </div>
        </div>

        {/* SVG Canvas */}
        <div className="relative flex justify-center py-4 bg-slate-950/70 rounded-lg mt-4 border border-slate-800/70 overflow-hidden">
          {loading && (
            <div className="absolute inset-0 bg-slate-950/80 flex items-center justify-center z-20">
              <div className="animate-spin inline-block w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full" />
            </div>
          )}

          <svg width={width} height={height} className="overflow-visible select-none">
            <defs>
              <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0.4" />
              </linearGradient>
            </defs>

            {/* Render Network Edges */}
            {edges.map((edge: any, i: number) => {
              const src = nodePositions[edge.source_id] || { x: centerX, y: centerY };
              const dst = nodePositions[edge.target_id] || { x: centerX, y: centerY };
              return (
                <g key={`edge-${i}`}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={dst.x}
                    y2={dst.y}
                    stroke="url(#edgeGrad)"
                    strokeWidth="1.5"
                    strokeDasharray={edge.relationship_type.includes('TRANSFER') ? '4 2' : 'none'}
                  />
                </g>
              );
            })}

            {/* Render Network Nodes */}
            {nodes.map((node: any) => {
              const pos = nodePositions[node.id] || { x: centerX, y: centerY };
              const isCenter = node.id === centerId;
              const isHighRisk = (node.risk_score || 0) >= 0.7;
              const color = getNodeColor(node.type, isHighRisk);
              const radius = isCenter ? 22 : 15;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-pointer group"
                  onClick={() => {
                    setCenterId(node.id);
                    fetchGraph(node.id);
                  }}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  {/* Glowing Halo for High-Risk or Center Nodes */}
                  {(isHighRisk || isCenter) && (
                    <circle
                      r={radius + 8}
                      fill={color}
                      fillOpacity="0.2"
                      className="animate-pulse"
                    />
                  )}

                  <circle
                    r={radius}
                    fill="#0b1120"
                    stroke={color}
                    strokeWidth={isCenter ? '3' : '2'}
                  />

                  {/* Icon Letter in Center */}
                  <text
                    textAnchor="middle"
                    dy=".3em"
                    fill={color}
                    fontSize={isCenter ? '12' : '10'}
                    fontWeight="bold"
                    fontFamily="monospace"
                  >
                    {node.type[0]}
                  </text>

                  {/* Node Label */}
                  <text
                    y={radius + 14}
                    textAnchor="middle"
                    fill="#cbd5e1"
                    fontSize="10"
                    fontFamily="monospace"
                  >
                    {node.id.length > 14 ? `${node.id.substring(0, 12)}...` : node.id}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Interactive Hover Tooltip */}
          {hoveredNode && (
            <div className="absolute top-4 left-4 bg-slate-900/95 border border-slate-700 p-3 rounded-lg text-xs shadow-xl backdrop-blur-md pointer-events-none z-10 w-64">
              <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                <span className="font-bold text-sky-400 font-mono">{hoveredNode.id}</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                  {hoveredNode.type}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-slate-300 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Connected Degree:</span>
                  <span className="font-mono">{hoveredNode.degree || 1} entities</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Risk Score:</span>
                  <span className="font-mono text-rose-400 font-bold">
                    {hoveredNode.risk_score ? `${(hoveredNode.risk_score * 100).toFixed(0)}%` : 'LOW'}
                  </span>
                </div>
                {hoveredNode.transaction_count && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Total Transactions:</span>
                    <span className="font-mono">{hoveredNode.transaction_count}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Entity Roster Table */}
        <div className="mt-4 pt-4 border-t border-slate-800">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
            Discovered Graph Entity Clusters
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
            {nodes.slice(0, 8).map((node: any) => (
              <div
                key={node.id}
                onClick={() => {
                  setCenterId(node.id);
                  fetchGraph(node.id);
                }}
                className="bg-slate-950 p-2.5 rounded border border-slate-800 hover:border-slate-700 cursor-pointer text-xs"
              >
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span className="font-semibold text-sky-400">{node.type}</span>
                  <span>Deg: {node.degree || 1}</span>
                </div>
                <div className="font-mono text-slate-200 truncate mt-0.5 font-medium">{node.id}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

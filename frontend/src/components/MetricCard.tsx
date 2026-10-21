import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  accent?: 'default' | 'danger' | 'warning' | 'success';
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtitle, accent = 'default' }) => {
  const borderColors = {
    default: 'border-slate-800',
    danger: 'border-red-800/70',
    warning: 'border-amber-800/70',
    success: 'border-emerald-800/70',
  };
  return (
    <div className={`bg-slate-900/90 border ${borderColors[accent]} rounded-lg p-4 shadow-sm`}>
      <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">{label}</div>
      <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">{value}</div>
      {subtitle && <div className="text-xs text-slate-400 mt-1">{subtitle}</div>}
    </div>
  );
};

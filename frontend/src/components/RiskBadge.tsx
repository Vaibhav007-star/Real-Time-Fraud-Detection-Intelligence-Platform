import React from 'react';
import { AlertSeverity, RiskCategory } from '../types';

export const RiskBadge: React.FC<{ category: RiskCategory | AlertSeverity }> = ({ category }) => {
  const styles: Record<string, string> = {
    HIGH_RISK: 'bg-red-950/80 text-red-300 border-red-700/70',
    CRITICAL: 'bg-red-950/90 text-red-200 border-red-600',
    HIGH: 'bg-orange-950/80 text-orange-300 border-orange-700/70',
    REVIEW: 'bg-amber-950/80 text-amber-300 border-amber-700/70',
    MEDIUM: 'bg-amber-950/80 text-amber-300 border-amber-700/70',
    LOW_RISK: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/70',
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-semibold rounded border ${styles[category] || styles.LOW_RISK}`}>
      {category}
    </span>
  );
};

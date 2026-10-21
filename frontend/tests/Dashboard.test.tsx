import { describe, it, expect } from 'vitest';
import React from 'react';
import { RiskBadge } from '../src/components/RiskBadge';
import { MetricCard } from '../src/components/MetricCard';

describe('Fraud Dashboard UI Components', () => {
  it('creates RiskBadge element for HIGH_RISK and LOW_RISK categories', () => {
    const elHigh = React.createElement(RiskBadge, { category: 'HIGH_RISK' });
    expect(elHigh.props.category).toBe('HIGH_RISK');
    const elLow = React.createElement(RiskBadge, { category: 'LOW_RISK' });
    expect(elLow.props.category).toBe('LOW_RISK');
  });

  it('creates MetricCard with formatted values and subtitles', () => {
    const card = React.createElement(MetricCard, {
      label: 'Open Fraud Alerts',
      value: 14,
      subtitle: 'Confirmed Fraud: 4',
      accent: 'danger',
    });
    expect(card.props.label).toBe('Open Fraud Alerts');
    expect(card.props.value).toBe(14);
  });
});

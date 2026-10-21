# Architecture Overview — Real-Time Fraud Detection Intelligence Platform

## 1. End-to-End Processing Pipeline

```
[REST API / CSV Upload / Synthetic Stream / Kafka Topic]
                         │
                         ▼
          ┌──────────────────────────────┐
          │   TransactionValidator       │ ──(Invalid / Malformed)──► [Dead-Letter Queue (DLQ)]
          │  • Schema & Amount Checks    │
          │  • Idempotent Dedup Cache    │
          │  • Watermark & Late-Event    │
          └──────────────┬───────────────┘
                         │ (fraud_label stripped before feature/scoring pipeline)
                         ▼
        ┌────────────────────────────────────────────────────────┐
        │             Multi-Pillar Detection Engine              │
        │                                                        │
        │  1. GraphFraudIntelligenceEngine (`app/graph/`)        │
        │     • Typed Nodes: ACCOUNT, DEVICE, IP, MERCHANT, TX   │
        │     • Shared-Device Rings, Circular Transfers (A→B→C→A)│
        │     • 1-2 Hop Local Neighborhood Risk & Degree Spike   │
        │                                                        │
        │  2. RealTimeFeatureEngine (`app/features/`)            │
        │     • Rolling 1m / 5m / 15m / 60m Velocity Windows     │
        │     • Account Z-Score & Ratio Deviation                │
        │     • Rapid Geo Shift & Declined-Then-Success Sequence │
        │                                                        │
        │  3. FraudMLPipeline (`app/ml/`)                        │
        │     • Class-Balanced Non-Linear Interaction Ensemble   │
        │     • Logistic Baseline Comparison & Anomaly Fallback  │
        │     • Local SHAP-Style Feature Attributions            │
        │                                                        │
        │  4. FraudRuleEngine (`app/rules/`)                     │
        │     • Explainable Domain Rules & Threshold Triggers    │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │   HybridRiskScoringEngine    │
                     │  • Configurable Weights      │
                     │  • Correlation Dampening     │
                     │  • LOW_RISK / REVIEW / HIGH  │
                     └──────────────┬───────────────┘
                                    │
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
  ┌─────────────────────────┐               ┌─────────────────────────┐
  │ Relational Persistence  │               │   AlertManager & WS     │
  │ • transactions, alerts  │               │ • Cooldown Suppression  │
  │ • investigation_cases   │               │ • Case & Audit History  │
  │ • analyst_notes, dlq    │               │ • Live WebSocket Push   │
  └─────────────────────────┘               └─────────────────────────┘
```

## 2. Key Architectural Decisions

1. **Strict Separation of Ingestion Time vs. Occurrence Time**:
   Every transaction records both `event_timestamp` (when the financial event occurred) and `ingestion_timestamp` (when the platform received it). A monotonic watermark tracks stream progress and flags out-of-order or late-arriving transactions (`is_late_event`, `late_by_seconds`).
2. **Zero Target Leakage Guarantee**:
   Optional ground-truth `fraud_label` fields on synthetic or historical evaluation records are stripped prior to calling `GraphFraudIntelligenceEngine`, `RealTimeFeatureEngine`, `FraudMLPipeline`, and `FraudRuleEngine`. Automated unit tests (`test_no_target_leakage_during_inference`) verify that identical transactions with `fraud_label=0` vs `fraud_label=1` receive bit-identical ML and hybrid risk scores.
3. **Bounded Memory for Streaming State**:
   - `RealTimeFeatureEngine` caps per-account rolling history (`max_events_per_account=250`) and total tracked accounts (`max_accounts=5000`).
   - `GraphFraudIntelligenceEngine` enforces `GRAPH_MAX_NODES`, `GRAPH_LOOKBACK_SECONDS`, and `GRAPH_MAX_TRAVERSAL_DEPTH` so neighborhood queries execute in bounded time without graph explosion.

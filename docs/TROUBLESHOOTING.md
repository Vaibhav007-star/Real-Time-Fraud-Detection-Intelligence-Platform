# Troubleshooting & Operations Guide

## 1. Common Startup & Environment Questions

### Q: Kafka broker is not running locally. Will the platform still stream and generate alerts?
**Yes.** By default, `STREAMING_MODE="in_process"` uses the built-in asynchronous streaming engine (`FraudPlatformOrchestrator`), which uses the exact same transaction validation, feature engineering, graph scoring, ML inference, and WebSocket alerting pipeline as Kafka mode. On **Page F (System Health)**, the dashboard explicitly distinguishes `LOCAL_DEMO_STREAMING` from `KAFKA_CLUSTER_STREAMING`.

### Q: How do I switch to a live Apache Kafka cluster?
1. Start Kafka via `docker compose up -d kafka` (or point to an existing cluster).
2. Set `STREAMING_MODE=kafka` and `KAFKA_BOOTSTRAP_SERVERS=localhost:9092` in `.env`.
3. Install `kafka-python` (`pip install kafka-python`) and restart the backend.

### Q: Why did a high-risk transaction not generate a second alert immediately?
The `AlertManager` enforces duplicate alert suppression (`ALERT_COOLDOWN_SECONDS=120` by default) keyed by `(account_id, triggered_rule_signature)`. If the same account triggers the same rule signature within the cooldown window and the combined score is below the critical override (`< 0.88`), the duplicate alert is suppressed and logged in `warnings` and on the **System Health** page (`Suppressed Duplicate Alerts`). You can set `Alert Cooldown (Seconds)` to `0` in **System Health & Config** to disable suppression during testing.

### Q: Where are rejected/malformed transactions stored?
Malformed transactions are never silently discarded. Any payload failing schema, timestamp, currency, or positive-amount validation is recorded in the `dead_letter_events` table and can be inspected via `GET /api/dlq` or on **Page F (System Health & Config)**.

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.alerts.manager import AlertManager
from app.api.websocket import WebSocketConnectionManager
from app.core.config import settings
from app.core.logging import get_logger
from app.database.db import DatabaseManager
from app.features.engine import RealTimeFeatureEngine
from app.graph.engine import GraphFraudIntelligenceEngine
from app.ingestion.generator import SyntheticTransactionGenerator
from app.ingestion.validator import TransactionValidator
from app.ml.pipeline import FraudMLPipeline
from app.monitoring.metrics import OperationalMetricsMonitor
from app.rules.engine import FraudRuleEngine
from app.scoring.hybrid import HybridRiskScoringEngine
from app.streaming.kafka_adapter import KafkaStreamAdapter

logger = get_logger("app.services.orchestrator")


class FraudPlatformOrchestrator:
    """End-to-end stateful orchestrator connecting Ingestion, Graph Analytics, Feature Engineering,
    Machine Learning, Rule Scoring, Hybrid Risk Aggregation, Alerting, Persistence, and Live Streaming.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db = DatabaseManager(db_path=db_path)
        self.validator = TransactionValidator(self.db)
        self.feature_engine = RealTimeFeatureEngine()
        self.graph_engine = GraphFraudIntelligenceEngine()
        self.ml_pipeline = FraudMLPipeline()
        self.rule_engine = FraudRuleEngine()
        self.hybrid_scorer = HybridRiskScoringEngine()
        self.alert_manager = AlertManager(self.db)
        self.metrics = OperationalMetricsMonitor()
        self.kafka = KafkaStreamAdapter()
        self.ws_manager = WebSocketConnectionManager()
        self.generator = SyntheticTransactionGenerator(seed=42)
        from app.ml.kaggle_benchmark import KaggleBenchmarkEngine
        self.kaggle_benchmark = KaggleBenchmarkEngine()

        # Ensure ML model is trained & metadata stored on startup
        if not self.ml_pipeline.model_loaded:
            report = self.ml_pipeline.train_and_evaluate(seed=42, num_streams=650)
            self.db.save_model_metadata(
                self.ml_pipeline.model_version,
                report["model_type"],
                report["trained_at"],
                self.ml_pipeline.feature_names,
                report,
            )
        else:
            rep = self.ml_pipeline.evaluation_report_
            if rep:
                self.db.save_model_metadata(
                    self.ml_pipeline.model_version,
                    rep.get("model_type", "Ensemble"),
                    rep.get("trained_at", datetime.now(timezone.utc).isoformat()),
                    self.ml_pipeline.feature_names,
                    rep,
                )

        # Background stream state
        self.stream_running: bool = False
        self.stream_paused: bool = False
        self.stream_tps: float = 2.0
        self.stream_fraud_rate: float = 0.18
        self._stream_task: Optional[asyncio.Task] = None
        self._replay_queue: List[Dict[str, Any]] = []

    def bootstrap_demo_seed_data(self, count: int = 28) -> None:
        """Populates initial realistic transactions and a couple of fraud scenarios if DB is empty."""
        agg = self.db.get_overview_aggregates()
        if agg["total_transactions"] > 0:
            return
        self.generator.reset_seed(42)
        initial_events = self.generator.generate_stream_batch(count=count, fraud_rate=0.15)
        initial_events.extend(self.generator.generate_scenario("shared_device_ring"))
        initial_events.extend(self.generator.generate_scenario("circular_money_mule"))
        for raw in initial_events:
            self.process_transaction_sync(raw)

    def process_transaction_sync(self, raw_payload: Dict[str, Any], bypass_cooldown: bool = False) -> Dict[str, Any]:
        """Synchronously validates, extracts graph & velocity features, runs ML & rules, persists, and creates alerts."""
        t0 = time.perf_counter()
        val_res = self.validator.validate_and_prepare(raw_payload)

        if not val_res.is_valid or val_res.validated_tx is None:
            self.metrics.record_error("ingestion.validator", val_res.error_reason or "Invalid event")
            return {
                "status": "REJECTED",
                "error": val_res.error_reason,
                "dlq_id": val_res.dlq_id,
                "ingestion_timestamp": val_res.ingestion_timestamp,
            }

        tx = val_res.validated_tx
        if val_res.is_duplicate:
            self.metrics.record_duplicate()
            existing = self.db.get_transaction(tx.transaction_id)
            if existing:
                existing["scoring_status"] = "IDEMPOTENT_DUPLICATE"
                existing["warnings"] = val_res.warnings
                return {"status": "DUPLICATE_IDEMPOTENT", "transaction": existing, "alert": None}

        # Crucial anti-leakage guardrail: strip `fraud_label` before passing to Graph, Feature, ML, or Rule engines
        if hasattr(tx, "model_copy"):
            tx_for_scoring = tx.model_copy(update={"fraud_label": None})
        elif hasattr(tx, "copy"):
            tx_for_scoring = tx.copy(update={"fraud_label": None})
        else:
            tx_for_scoring = tx

        # 1. Graph analytics & topology update
        graph_features, graph_score, graph_explanations = self.graph_engine.analyze_and_record_transaction(
            tx_for_scoring
        )

        # 2. Rolling velocity & behavioral feature extraction
        features = self.feature_engine.compute_and_update(tx_for_scoring, graph_features)

        # 3. Supervised ML inference (or explicit anomaly fallback)
        ml_result = self.ml_pipeline.score_features(features)
        ml_score = float(ml_result["ml_score"])

        # 4. Rule engine evaluation
        rule_score, triggered_rules = self.rule_engine.evaluate(tx_for_scoring, features)

        # 5. Hybrid risk aggregation
        hybrid_result = self.hybrid_scorer.compute_hybrid_score(
            ml_score=ml_score,
            graph_score=graph_score,
            rule_score=rule_score,
            triggered_rules=triggered_rules,
            graph_explanations=graph_explanations,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        all_warnings = val_res.warnings + ml_result.get("warnings", []) + hybrid_result.get("warnings", [])

        scored_tx: Dict[str, Any] = {
            "transaction_id": tx.transaction_id,
            "event_timestamp": tx.timestamp,
            "ingestion_timestamp": val_res.ingestion_timestamp,
            "scoring_timestamp": ml_result["scoring_timestamp"],
            "source_account_id": tx.source_account_id,
            "destination_account_id": tx.destination_account_id,
            "merchant_id": tx.merchant_id,
            "merchant_category": tx.merchant_category,
            "device_id": tx.device_id,
            "ip_address": tx.ip_address,
            "transaction_amount": tx.transaction_amount,
            "currency": tx.currency,
            "transaction_type": tx.transaction_type,
            "location": tx.location,
            "transaction_status": tx.transaction_status,
            "fraud_label": tx.fraud_label,  # Stored strictly for post-hoc evaluation metrics
            "is_demo": tx.is_demo,
            "scenario_tag": tx.scenario_tag,
            "is_late_event": val_res.is_late_event,
            "late_by_seconds": val_res.late_by_seconds,
            "ml_score": ml_score,
            "graph_score": graph_score,
            "rule_score": rule_score,
            "combined_score": hybrid_result["combined_score"],
            "risk_percentage": hybrid_result["risk_percentage"],
            "risk_category": hybrid_result["risk_category"],
            "predicted_class": 1 if hybrid_result["combined_score"] >= settings.threshold_review else 0,
            "model_version": ml_result["model_version"],
            "scoring_method": ml_result["scoring_method"],
            "scoring_status": ml_result["scoring_status"],
            "warnings": all_warnings,
            "triggered_rules": triggered_rules,
            "top_risk_factors": ml_result["top_risk_factors"],
            "graph_explanations": graph_explanations,
            "features": features,
            "alert_id": None,
            "processing_latency_ms": latency_ms,
        }

        # Persist transaction first (satisfies foreign key for alert)
        self.db.save_scored_transaction(scored_tx)

        # 6. Evaluate live fraud alert creation
        alert_record, suppressed = self.alert_manager.evaluate_and_create_alert(scored_tx, bypass_cooldown=bypass_cooldown)
        if alert_record:
            scored_tx["alert_id"] = alert_record["alert_id"]
            with self.db.connection() as conn:
                conn.execute(
                    "UPDATE transactions SET alert_id = ? WHERE transaction_id = ?",
                    (alert_record["alert_id"], tx.transaction_id),
                )
        elif suppressed:
            scored_tx["warnings"].append("Duplicate alert suppressed by active account/rule cooldown policy.")

        # 7. Publish to Kafka if configured and connected
        self.kafka.publish_transaction(scored_tx)
        if alert_record:
            self.kafka.publish_alert(alert_record)

        self.metrics.record_processed(latency_ms=latency_ms, is_late=val_res.is_late_event)
        return {"status": "PROCESSED", "transaction": scored_tx, "alert": alert_record}

    async def process_transaction_async(self, raw_payload: Dict[str, Any], bypass_cooldown: bool = False) -> Dict[str, Any]:
        result = self.process_transaction_sync(raw_payload, bypass_cooldown=bypass_cooldown)
        if result["status"] == "PROCESSED":
            await self.ws_manager.broadcast("TRANSACTION_SCORED", result["transaction"])
            if result.get("alert"):
                await self.ws_manager.broadcast("ALERT_CREATED", result["alert"])
        return result

    async def _stream_loop(self) -> None:
        while self.stream_running:
            if self.stream_paused:
                await asyncio.sleep(0.25)
                continue
            try:
                if self._replay_queue:
                    raw_ev = self._replay_queue.pop(0)
                    await self.process_transaction_async(raw_ev)
                else:
                    batch = self.generator.generate_stream_batch(
                        count=1, fraud_rate=self.stream_fraud_rate
                    )
                    for raw_ev in batch:
                        if not self.stream_running or self.stream_paused:
                            break
                        await self.process_transaction_async(raw_ev)
                        await asyncio.sleep(max(0.04, 1.0 / max(0.2, self.stream_tps)))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.metrics.record_error("streaming.loop", str(exc))
                await asyncio.sleep(0.5)

    async def start_stream(self, tps: float = 2.0, fraud_rate: float = 0.18, seed: Optional[int] = None) -> Dict[str, Any]:
        self.stream_tps = max(0.2, min(50.0, float(tps)))
        self.stream_fraud_rate = max(0.0, min(1.0, float(fraud_rate)))
        if seed is not None:
            self.generator.reset_seed(int(seed))
        self.stream_paused = False
        if not self.stream_running:
            self.stream_running = True
            self._stream_task = asyncio.create_task(self._stream_loop())
        return self.stream_status()

    async def stop_stream(self) -> Dict[str, Any]:
        self.stream_running = False
        self.stream_paused = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._stream_task = None
        return self.stream_status()

    def pause_or_resume_stream(self, pause: bool) -> Dict[str, Any]:
        self.stream_paused = bool(pause)
        return self.stream_status()

    def stream_status(self) -> Dict[str, Any]:
        return {
            "running": self.stream_running,
            "paused": self.stream_paused,
            "configured_tps": self.stream_tps,
            "measured_tps": self.metrics.current_tps(),
            "fraud_injection_rate": self.stream_fraud_rate,
            "replay_queue_remaining": len(self._replay_queue),
            "streaming_adapter": self.kafka.health_status(),
        }

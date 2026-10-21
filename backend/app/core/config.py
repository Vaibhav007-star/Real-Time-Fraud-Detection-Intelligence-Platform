import os
from pathlib import Path
from typing import List, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings:
    """Centralized environment-driven configuration for the Fraud Detection Platform."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "Real-Time Fraud Detection Intelligence Platform")
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))

        raw_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:8000,http://127.0.0.1:8000,http://127.0.0.1:5173",
        )
        self.cors_origins: List[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]

        default_db_path = BASE_PROJECT_DIR / "data" / "fraud_platform.db"
        self.database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")
        self.sqlite_path: str = (
            self.database_url.replace("sqlite:///", "")
            if self.database_url.startswith("sqlite:///")
            else str(default_db_path)
        )

        # Streaming & Kafka settings
        self.streaming_mode: str = os.getenv("STREAMING_MODE", "in_process")  # "in_process" or "kafka"
        self.kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.kafka_transaction_topic: str = os.getenv("KAFKA_TRANSACTION_TOPIC", "financial.transactions.v1")
        self.kafka_alert_topic: str = os.getenv("KAFKA_ALERT_TOPIC", "fraud.alerts.v1")
        self.kafka_dlq_topic: str = os.getenv("KAFKA_DLQ_TOPIC", "financial.transactions.dlq.v1")
        self.kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "fraud-intelligence-engine")

        # Hybrid Risk Scoring Weights
        self.weight_ml_score: float = float(os.getenv("WEIGHT_ML_SCORE", "0.45"))
        self.weight_graph_score: float = float(os.getenv("WEIGHT_GRAPH_SCORE", "0.30"))
        self.weight_rule_score: float = float(os.getenv("WEIGHT_RULE_SCORE", "0.25"))

        # Thresholds
        self.threshold_review: float = float(os.getenv("THRESHOLD_REVIEW", "0.45"))
        self.threshold_high_risk: float = float(os.getenv("THRESHOLD_HIGH_RISK", "0.72"))

        # Alert & Late Event Windows
        self.alert_cooldown_seconds: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "120"))
        self.max_late_event_seconds: int = int(os.getenv("MAX_LATE_EVENT_SECONDS", "86400"))

        # Graph & Feature Memory Bounds
        self.graph_max_nodes: int = int(os.getenv("GRAPH_MAX_NODES", "10000"))
        self.graph_lookback_seconds: int = int(os.getenv("GRAPH_LOOKBACK_SECONDS", "86400"))
        self.graph_max_traversal_depth: int = int(os.getenv("GRAPH_MAX_TRAVERSAL_DEPTH", "3"))
        self.feature_window_max_events: int = int(os.getenv("FEATURE_WINDOW_MAX_EVENTS", "5000"))

        # Paths
        self.model_dir: Path = BASE_PROJECT_DIR / "models"
        self.sample_data_dir: Path = BASE_PROJECT_DIR / "data" / "sample"
        self.max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

    def update_scoring_config(
        self,
        weight_ml: float,
        weight_graph: float,
        weight_rule: float,
        threshold_review: float,
        threshold_high_risk: float,
        alert_cooldown_seconds: int,
    ) -> Dict[str, Any]:
        total = weight_ml + weight_graph + weight_rule
        if total <= 0:
            raise ValueError("Sum of scoring weights must be positive.")
        self.weight_ml_score = round(weight_ml / total, 4)
        self.weight_graph_score = round(weight_graph / total, 4)
        self.weight_rule_score = round(1.0 - self.weight_ml_score - self.weight_graph_score, 4)
        if not (0.0 < threshold_review < threshold_high_risk <= 1.0):
            raise ValueError("Thresholds must satisfy 0 < threshold_review < threshold_high_risk <= 1.0")
        self.threshold_review = threshold_review
        self.threshold_high_risk = threshold_high_risk
        self.alert_cooldown_seconds = max(0, int(alert_cooldown_seconds))
        return self.to_public_dict()

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "streaming_mode": self.streaming_mode,
            "kafka_bootstrap_servers": self.kafka_bootstrap_servers,
            "kafka_transaction_topic": self.kafka_transaction_topic,
            "weights": {
                "ml_score": self.weight_ml_score,
                "graph_score": self.weight_graph_score,
                "rule_score": self.weight_rule_score,
            },
            "thresholds": {
                "review": self.threshold_review,
                "high_risk": self.threshold_high_risk,
            },
            "alert_cooldown_seconds": self.alert_cooldown_seconds,
            "max_late_event_seconds": self.max_late_event_seconds,
            "graph_bounds": {
                "max_nodes": self.graph_max_nodes,
                "lookback_seconds": self.graph_lookback_seconds,
                "max_traversal_depth": self.graph_max_traversal_depth,
            },
            "feature_window_max_events": self.feature_window_max_events,
            "max_upload_bytes": self.max_upload_bytes,
        }


settings = Settings()

import json
from typing import Any, Callable, Dict, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.streaming.kafka")

try:
    from kafka import KafkaProducer, KafkaConsumer  # type: ignore
    KAFKA_CLIENT_INSTALLED = True
except ImportError:
    KAFKA_CLIENT_INSTALLED = False


class KafkaStreamAdapter:
    """Kafka streaming adapter with automatic fallback diagnostics when no broker is reachable."""

    def __init__(self) -> None:
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.tx_topic = settings.kafka_transaction_topic
        self.alert_topic = settings.kafka_alert_topic
        self.dlq_topic = settings.kafka_dlq_topic
        self._producer: Optional[Any] = None
        self.connected: bool = False
        self.last_error: Optional[str] = None

        if settings.streaming_mode == "kafka":
            self._try_connect()
        else:
            self.last_error = "Configured in 'in_process' mode (set STREAMING_MODE=kafka to enable broker connection)."

    def _try_connect(self) -> bool:
        if not KAFKA_CLIENT_INSTALLED:
            self.connected = False
            self.last_error = "kafka-python library not installed; using in-process streaming adapter."
            return False
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=2500,
                max_block_ms=2500,
                retries=2,
            )
            self.connected = True
            self.last_error = None
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = f"Kafka broker unreachable at {self.bootstrap_servers}: {exc}"
            return False

    def publish_transaction(self, event: Dict[str, Any]) -> bool:
        if not self.connected or self._producer is None:
            return False
        try:
            self._producer.send(self.tx_topic, value=event)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.connected = False
            return False

    def publish_alert(self, alert: Dict[str, Any]) -> bool:
        if not self.connected or self._producer is None:
            return False
        try:
            self._producer.send(self.alert_topic, value=alert)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def health_status(self) -> Dict[str, Any]:
        return {
            "configured_mode": settings.streaming_mode,
            "active_adapter": "kafka" if self.connected else "in_process",
            "kafka_client_installed": KAFKA_CLIENT_INSTALLED,
            "bootstrap_servers": self.bootstrap_servers,
            "transaction_topic": self.tx_topic,
            "alert_topic": self.alert_topic,
            "dlq_topic": self.dlq_topic,
            "broker_connected": self.connected,
            "diagnostic": self.last_error or "Connected to Kafka cluster",
        }

from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError
from app.core.config import settings
from app.core.logging import get_logger
from app.database.db import DatabaseManager
from app.schemas.transaction import TransactionCreate

logger = get_logger("app.ingestion.validator")


class IngestionValidationResult:
    def __init__(
        self,
        is_valid: bool,
        is_duplicate: bool = False,
        validated_tx: Optional[TransactionCreate] = None,
        ingestion_timestamp: Optional[str] = None,
        is_late_event: bool = False,
        late_by_seconds: float = 0.0,
        warnings: Optional[List[str]] = None,
        error_reason: Optional[str] = None,
        dlq_id: Optional[int] = None,
    ) -> None:
        self.is_valid = is_valid
        self.is_duplicate = is_duplicate
        self.validated_tx = validated_tx
        self.ingestion_timestamp = ingestion_timestamp or datetime.now(timezone.utc).isoformat()
        self.is_late_event = is_late_event
        self.late_by_seconds = late_by_seconds
        self.warnings = warnings or []
        self.error_reason = error_reason
        self.dlq_id = dlq_id


class TransactionValidator:
    """Validates incoming transaction payloads, enforces idempotency, detects late events, and routes failures to DLQ."""

    def __init__(self, db: DatabaseManager, max_seen_cache: int = 10000) -> None:
        self.db = db
        self.max_seen_cache = max_seen_cache
        self._seen_tx_ids: OrderedDict[str, str] = OrderedDict()
        self._latest_watermark: Optional[datetime] = None

    def validate_and_prepare(self, raw_payload: Dict[str, Any]) -> IngestionValidationResult:
        ingestion_dt = datetime.now(timezone.utc)
        ingestion_iso = ingestion_dt.isoformat()

        if not isinstance(raw_payload, dict):
            dlq_id = self.db.record_dead_letter(raw_payload, "Payload must be a JSON object")
            return IngestionValidationResult(
                is_valid=False,
                error_reason="Payload must be a JSON object",
                dlq_id=dlq_id,
                ingestion_timestamp=ingestion_iso,
            )

        # Required field presence check before schema parsing
        required_fields = [
            "transaction_id",
            "timestamp",
            "source_account_id",
            "device_id",
            "ip_address",
            "transaction_amount",
        ]
        missing = [f for f in required_fields if f not in raw_payload or raw_payload.get(f) in (None, "")]
        if missing:
            reason = f"Missing required fields: {', '.join(missing)}"
            dlq_id = self.db.record_dead_letter(raw_payload, reason)
            return IngestionValidationResult(
                is_valid=False,
                error_reason=reason,
                dlq_id=dlq_id,
                ingestion_timestamp=ingestion_iso,
            )

        try:
            tx = TransactionCreate(**raw_payload)
        except ValidationError as exc:
            reason = f"Schema validation error: {exc}"
            dlq_id = self.db.record_dead_letter(raw_payload, reason)
            return IngestionValidationResult(
                is_valid=False,
                error_reason=reason,
                dlq_id=dlq_id,
                ingestion_timestamp=ingestion_iso,
            )
        except Exception as exc:
            reason = f"Invalid transaction payload: {exc}"
            dlq_id = self.db.record_dead_letter(raw_payload, reason)
            return IngestionValidationResult(
                is_valid=False,
                error_reason=reason,
                dlq_id=dlq_id,
                ingestion_timestamp=ingestion_iso,
            )

        # Duplicate / idempotency check
        if tx.transaction_id in self._seen_tx_ids or self.db.transaction_exists(tx.transaction_id):
            return IngestionValidationResult(
                is_valid=True,
                is_duplicate=True,
                validated_tx=tx,
                ingestion_timestamp=ingestion_iso,
                warnings=[f"Duplicate event '{tx.transaction_id}' detected; returning idempotent result."],
            )

        # Event-time vs Ingestion-time & watermark check for late-arriving or out-of-order events
        event_dt = datetime.fromisoformat(tx.timestamp)
        warnings: List[str] = []
        is_late = False
        late_seconds = 0.0

        # Compare against stream watermark and wall-clock ingestion time
        reference_dt = self._latest_watermark if self._latest_watermark and self._latest_watermark > ingestion_dt else ingestion_dt
        if self._latest_watermark and event_dt < self._latest_watermark:
            watermark_lag = (self._latest_watermark - event_dt).total_seconds()
            if watermark_lag > 5.0:
                is_late = True
                late_seconds = round(watermark_lag, 2)
                warnings.append(
                    f"Out-of-order/late event relative to stream watermark by {late_seconds:.1f}s."
                )

        wall_clock_lag = (ingestion_dt - event_dt).total_seconds()
        if wall_clock_lag > 300.0 and not is_late:
            is_late = True
            late_seconds = round(wall_clock_lag, 2)
            warnings.append(f"Late-arriving event relative to ingestion time by {late_seconds:.1f}s.")

        if wall_clock_lag > settings.max_late_event_seconds:
            warnings.append(
                f"Event age ({wall_clock_lag:.0f}s) exceeds configured window ({settings.max_late_event_seconds}s); processed with historical window warning."
            )

        if self._latest_watermark is None or event_dt > self._latest_watermark:
            self._latest_watermark = event_dt

        self._seen_tx_ids[tx.transaction_id] = ingestion_iso
        if len(self._seen_tx_ids) > self.max_seen_cache:
            self._seen_tx_ids.popitem(last=False)

        return IngestionValidationResult(
            is_valid=True,
            is_duplicate=False,
            validated_tx=tx,
            ingestion_timestamp=ingestion_iso,
            is_late_event=is_late,
            late_by_seconds=late_seconds,
            warnings=warnings,
        )

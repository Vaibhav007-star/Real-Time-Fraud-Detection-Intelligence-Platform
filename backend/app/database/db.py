import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.database")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    tx_count INTEGER NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    risk_tier TEXT NOT NULL DEFAULT 'LOW_RISK'
);

CREATE TABLE IF NOT EXISTS merchants (
    merchant_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tx_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    first_seen_at TEXT NOT NULL,
    last_ip TEXT,
    account_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    event_timestamp TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    scoring_timestamp TEXT NOT NULL,
    source_account_id TEXT NOT NULL,
    destination_account_id TEXT,
    merchant_id TEXT,
    merchant_category TEXT,
    device_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    transaction_amount REAL NOT NULL,
    currency TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    location TEXT,
    transaction_status TEXT NOT NULL,
    fraud_label INTEGER,
    is_demo INTEGER NOT NULL DEFAULT 0,
    scenario_tag TEXT,
    is_late_event INTEGER NOT NULL DEFAULT 0,
    late_by_seconds REAL NOT NULL DEFAULT 0.0,
    ml_score REAL NOT NULL,
    graph_score REAL NOT NULL,
    rule_score REAL NOT NULL,
    combined_score REAL NOT NULL,
    risk_percentage REAL NOT NULL,
    risk_category TEXT NOT NULL,
    predicted_class INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    scoring_method TEXT NOT NULL,
    scoring_status TEXT NOT NULL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    triggered_rules_json TEXT NOT NULL DEFAULT '[]',
    top_risk_factors_json TEXT NOT NULL DEFAULT '[]',
    graph_explanations_json TEXT NOT NULL DEFAULT '[]',
    features_json TEXT NOT NULL DEFAULT '{}',
    alert_id TEXT,
    processing_latency_ms REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (source_account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE INDEX IF NOT EXISTS idx_tx_event_ts ON transactions(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tx_source_acc ON transactions(source_account_id);
CREATE INDEX IF NOT EXISTS idx_tx_risk_cat ON transactions(risk_category);
CREATE INDEX IF NOT EXISTS idx_tx_combined_score ON transactions(combined_score DESC);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    merchant_id TEXT,
    transaction_amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    detection_timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL,
    risk_percentage REAL NOT NULL,
    ml_score REAL NOT NULL,
    graph_score REAL NOT NULL,
    rule_score REAL NOT NULL,
    severity TEXT NOT NULL,
    risk_category TEXT NOT NULL,
    detection_method TEXT NOT NULL,
    triggered_rules_json TEXT NOT NULL DEFAULT '[]',
    model_explanation_json TEXT NOT NULL DEFAULT '[]',
    graph_relationships_json TEXT NOT NULL DEFAULT '[]',
    investigation_status TEXT NOT NULL DEFAULT 'OPEN',
    assigned_to TEXT,
    resolution_outcome TEXT NOT NULL DEFAULT 'UNRESOLVED',
    is_demo INTEGER NOT NULL DEFAULT 0,
    scenario_tag TEXT,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(detection_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(investigation_status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_account ON alerts(account_id);

CREATE TABLE IF NOT EXISTS investigation_cases (
    case_id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    assigned_analyst TEXT,
    resolution_outcome TEXT NOT NULL DEFAULT 'UNRESOLVED',
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);

CREATE TABLE IF NOT EXISTS analyst_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    author TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dead_letter_events (
    dlq_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_payload_json TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_metadata (
    model_version TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    trained_at TEXT NOT NULL,
    feature_names_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
"""


class DatabaseManager:
    """Thread-safe relational database manager with migrations and transaction safety."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.configured_path = db_path or settings.sqlite_path
        self.db_path = self.configured_path
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            # Probe whether the target filesystem supports SQLite POSIX file locking
            try:
                probe = sqlite3.connect(self.db_path, timeout=0.1)
                probe.execute("CREATE TABLE IF NOT EXISTS _lock_probe (id INTEGER PRIMARY KEY);")
                probe.commit()
                probe.close()
            except sqlite3.OperationalError:
                import hashlib, tempfile
                digest = hashlib.md5(str(self.configured_path).encode("utf-8")).hexdigest()[:10]
                self.db_path = str(Path(tempfile.gettempdir()) / f"fraud_platform_{digest}.db")
        self._lock = threading.RLock()
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        self.run_migrations()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            if self._persistent_conn is not None:
                try:
                    yield self._persistent_conn
                    self._persistent_conn.commit()
                except Exception:
                    self._persistent_conn.rollback()
                    raise
            else:
                conn = sqlite3.connect(self.db_path, timeout=15.0, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode = MEMORY;")
                conn.execute("PRAGMA foreign_keys = ON;")
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

    def run_migrations(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
            cur = conn.execute("SELECT COUNT(*) as cnt FROM schema_migrations WHERE version = 1")
            if cur.fetchone()["cnt"] == 0:
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (1, "001_initial_fraud_intelligence_schema", datetime.now(timezone.utc).isoformat()),
                )

    def check_health(self) -> Dict[str, Any]:
        try:
            with self.connection() as conn:
                cur = conn.execute("SELECT COUNT(*) AS tx_cnt FROM transactions")
                tx_cnt = cur.fetchone()["tx_cnt"]
                cur_a = conn.execute("SELECT COUNT(*) AS al_cnt FROM alerts")
                al_cnt = cur_a.fetchone()["al_cnt"]
            return {
                "status": "healthy",
                "engine": "sqlite3 (foreign_keys=ON)",
                "database_path": self.db_path,
                "transactions_stored": tx_cnt,
                "alerts_stored": al_cnt,
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def transaction_exists(self, transaction_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM transactions WHERE transaction_id = ?", (transaction_id,)
            ).fetchone()
            return row is not None

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
            ).fetchone()
            return self._row_to_tx_dict(row) if row else None

    def save_scored_transaction(self, tx: Dict[str, Any]) -> None:
        with self.connection() as conn:
            now_iso = tx["ingestion_timestamp"]
            # Upsert Account
            conn.execute(
                """
                INSERT INTO accounts (account_id, created_at, last_seen_at, tx_count, total_amount, risk_tier)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    tx_count = accounts.tx_count + 1,
                    total_amount = accounts.total_amount + excluded.total_amount,
                    risk_tier = CASE
                        WHEN excluded.risk_tier = 'HIGH_RISK' THEN 'HIGH_RISK'
                        WHEN accounts.risk_tier = 'HIGH_RISK' THEN 'HIGH_RISK'
                        ELSE excluded.risk_tier
                    END
                """,
                (
                    tx["source_account_id"],
                    now_iso,
                    tx["event_timestamp"],
                    tx["transaction_amount"],
                    tx["risk_category"],
                ),
            )
            # Upsert Merchant if present
            if tx.get("merchant_id"):
                conn.execute(
                    """
                    INSERT INTO merchants (merchant_id, category, created_at, tx_count)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(merchant_id) DO UPDATE SET
                        tx_count = merchants.tx_count + 1
                    """,
                    (tx["merchant_id"], tx.get("merchant_category") or "GENERAL_RETAIL", now_iso),
                )
            # Upsert Device
            conn.execute(
                """
                INSERT INTO devices (device_id, first_seen_at, last_ip, account_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_ip = excluded.last_ip
                """,
                (tx["device_id"], now_iso, tx["ip_address"]),
            )
            # Insert Transaction
            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id, event_timestamp, ingestion_timestamp, scoring_timestamp,
                    source_account_id, destination_account_id, merchant_id, merchant_category,
                    device_id, ip_address, transaction_amount, currency, transaction_type,
                    location, transaction_status, fraud_label, is_demo, scenario_tag,
                    is_late_event, late_by_seconds, ml_score, graph_score, rule_score,
                    combined_score, risk_percentage, risk_category, predicted_class,
                    model_version, scoring_method, scoring_status, warnings_json,
                    triggered_rules_json, top_risk_factors_json, graph_explanations_json,
                    features_json, alert_id, processing_latency_ms
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    tx["transaction_id"],
                    tx["event_timestamp"],
                    tx["ingestion_timestamp"],
                    tx["scoring_timestamp"],
                    tx["source_account_id"],
                    tx.get("destination_account_id"),
                    tx.get("merchant_id"),
                    tx.get("merchant_category"),
                    tx["device_id"],
                    tx["ip_address"],
                    tx["transaction_amount"],
                    tx["currency"],
                    tx["transaction_type"],
                    tx.get("location"),
                    tx["transaction_status"],
                    tx.get("fraud_label"),
                    1 if tx.get("is_demo") else 0,
                    tx.get("scenario_tag"),
                    1 if tx.get("is_late_event") else 0,
                    tx.get("late_by_seconds", 0.0),
                    tx["ml_score"],
                    tx["graph_score"],
                    tx["rule_score"],
                    tx["combined_score"],
                    tx["risk_percentage"],
                    tx["risk_category"],
                    tx["predicted_class"],
                    tx["model_version"],
                    tx["scoring_method"],
                    tx["scoring_status"],
                    json.dumps(tx.get("warnings", [])),
                    json.dumps(tx.get("triggered_rules", [])),
                    json.dumps(tx.get("top_risk_factors", [])),
                    json.dumps(tx.get("graph_explanations", [])),
                    json.dumps(tx.get("features", {})),
                    tx.get("alert_id"),
                    tx.get("processing_latency_ms", 0.0),
                ),
            )

    def _row_to_tx_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_demo"] = bool(d.get("is_demo"))
        d["is_late_event"] = bool(d.get("is_late_event"))
        d["warnings"] = json.loads(d.pop("warnings_json", "[]"))
        d["triggered_rules"] = json.loads(d.pop("triggered_rules_json", "[]"))
        d["top_risk_factors"] = json.loads(d.pop("top_risk_factors_json", "[]"))
        d["graph_explanations"] = json.loads(d.pop("graph_explanations_json", "[]"))
        d["features"] = json.loads(d.pop("features_json", "{}"))
        return d

    def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_category: Optional[str] = None,
        search: Optional[str] = None,
        min_score: Optional[float] = None,
        sort_by: str = "event_timestamp",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        allowed_sort = {
            "event_timestamp": "event_timestamp",
            "transaction_amount": "transaction_amount",
            "combined_score": "combined_score",
            "ml_score": "ml_score",
            "graph_score": "graph_score",
        }
        col = allowed_sort.get(sort_by, "event_timestamp")
        direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        clauses: List[str] = []
        params: List[Any] = []
        if risk_category and risk_category != "ALL":
            clauses.append("risk_category = ?")
            params.append(risk_category.upper())
        if min_score is not None:
            clauses.append("combined_score >= ?")
            params.append(float(min_score))
        if search:
            q = f"%{search.strip()}%"
            clauses.append(
                "(transaction_id LIKE ? OR source_account_id LIKE ? OR COALESCE(merchant_id, '') LIKE ? OR device_id LIKE ?)"
            )
            params.extend([q, q, q, q])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connection() as conn:
            cnt_row = conn.execute(f"SELECT COUNT(*) AS cnt FROM transactions {where_sql}", params).fetchone()
            total = cnt_row["cnt"]
            rows = conn.execute(
                f"SELECT * FROM transactions {where_sql} ORDER BY {col} {direction}, ingestion_timestamp DESC LIMIT ? OFFSET ?",
                params + [int(limit), int(offset)],
            ).fetchall()
            return [self._row_to_tx_dict(r) for r in rows], total

    def save_alert(self, alert: Dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO alerts (
                    alert_id, transaction_id, account_id, merchant_id, transaction_amount,
                    currency, detection_timestamp, risk_score, risk_percentage,
                    ml_score, graph_score, rule_score, severity, risk_category,
                    detection_method, triggered_rules_json, model_explanation_json,
                    graph_relationships_json, investigation_status, assigned_to,
                    resolution_outcome, is_demo, scenario_tag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["alert_id"],
                    alert["transaction_id"],
                    alert["account_id"],
                    alert.get("merchant_id"),
                    alert["transaction_amount"],
                    alert.get("currency", "USD"),
                    alert["detection_timestamp"],
                    alert["risk_score"],
                    alert["risk_percentage"],
                    alert["ml_score"],
                    alert["graph_score"],
                    alert["rule_score"],
                    alert["severity"],
                    alert["risk_category"],
                    alert["detection_method"],
                    json.dumps(alert.get("triggered_rules", [])),
                    json.dumps(alert.get("model_explanation", [])),
                    json.dumps(alert.get("graph_relationships", [])),
                    alert.get("investigation_status", "OPEN"),
                    alert.get("assigned_to"),
                    alert.get("resolution_outcome", "UNRESOLVED"),
                    1 if alert.get("is_demo") else 0,
                    alert.get("scenario_tag"),
                ),
            )
            conn.execute(
                """
                INSERT INTO investigation_cases (
                    case_id, alert_id, account_id, opened_at, updated_at, status, assigned_analyst, resolution_outcome
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"CASE-{alert['alert_id']}",
                    alert["alert_id"],
                    alert["account_id"],
                    alert["detection_timestamp"],
                    alert["detection_timestamp"],
                    alert.get("investigation_status", "OPEN"),
                    alert.get("assigned_to"),
                    alert.get("resolution_outcome", "UNRESOLVED"),
                ),
            )
            conn.execute(
                """
                INSERT INTO audit_events (entity_type, entity_id, action, actor, details_json, created_at)
                VALUES ('ALERT', ?, 'ALERT_CREATED', 'system.detector', ?, ?)
                """,
                (
                    alert["alert_id"],
                    json.dumps({"severity": alert["severity"], "risk_score": alert["risk_score"]}),
                    alert["detection_timestamp"],
                ),
            )

    def _row_to_alert_dict(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_demo"] = bool(d.get("is_demo"))
        d["triggered_rules"] = json.loads(d.pop("triggered_rules_json", "[]"))
        d["model_explanation"] = json.loads(d.pop("model_explanation_json", "[]"))
        d["graph_relationships"] = json.loads(d.pop("graph_relationships_json", "[]"))
        notes_rows = conn.execute(
            "SELECT note_id, author, note, created_at FROM analyst_notes WHERE alert_id = ? ORDER BY note_id ASC",
            (d["alert_id"],),
        ).fetchall()
        d["notes"] = [dict(n) for n in notes_rows]
        audit_rows = conn.execute(
            "SELECT event_id, action, actor, details_json, created_at FROM audit_events WHERE entity_type = 'ALERT' AND entity_id = ? ORDER BY event_id ASC",
            (d["alert_id"],),
        ).fetchall()
        d["audit_history"] = [
            {
                "event_id": a["event_id"],
                "action": a["action"],
                "actor": a["actor"],
                "details": json.loads(a["details_json"]),
                "created_at": a["created_at"],
            }
            for a in audit_rows
        ]
        return d

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            return self._row_to_alert_dict(conn, row) if row else None

    def list_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        resolved_only: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        clauses: List[str] = []
        params: List[Any] = []
        if severity and severity != "ALL":
            clauses.append("severity = ?")
            params.append(severity.upper())
        if status and status != "ALL":
            clauses.append("investigation_status = ?")
            params.append(status.upper())
        if resolved_only is True:
            clauses.append("investigation_status = 'RESOLVED'")
        elif resolved_only is False:
            clauses.append("investigation_status != 'RESOLVED'")
        if search:
            q = f"%{search.strip()}%"
            clauses.append("(alert_id LIKE ? OR transaction_id LIKE ? OR account_id LIKE ?)")
            params.extend([q, q, q])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connection() as conn:
            cnt = conn.execute(f"SELECT COUNT(*) AS cnt FROM alerts {where_sql}", params).fetchone()["cnt"]
            rows = conn.execute(
                f"SELECT * FROM alerts {where_sql} ORDER BY detection_timestamp DESC LIMIT ? OFFSET ?",
                params + [int(limit), int(offset)],
            ).fetchall()
            return [self._row_to_alert_dict(conn, r) for r in rows], cnt

    def update_alert_investigation(
        self,
        alert_id: str,
        status: str,
        assigned_to: Optional[str],
        resolution_outcome: Optional[str],
        note: Optional[str],
        actor: str,
    ) -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            existing = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            if not existing:
                return None
            new_assigned = assigned_to if assigned_to is not None else existing["assigned_to"]
            new_resolution = resolution_outcome if resolution_outcome is not None else existing["resolution_outcome"]
            conn.execute(
                """
                UPDATE alerts
                SET investigation_status = ?, assigned_to = ?, resolution_outcome = ?
                WHERE alert_id = ?
                """,
                (status, new_assigned, new_resolution, alert_id),
            )
            conn.execute(
                """
                UPDATE investigation_cases
                SET status = ?, assigned_analyst = ?, resolution_outcome = ?, updated_at = ?
                WHERE alert_id = ?
                """,
                (status, new_assigned, new_resolution, now_iso, alert_id),
            )
            if note and note.strip():
                conn.execute(
                    "INSERT INTO analyst_notes (alert_id, author, note, created_at) VALUES (?, ?, ?, ?)",
                    (alert_id, actor, note.strip(), now_iso),
                )
            conn.execute(
                """
                INSERT INTO audit_events (entity_type, entity_id, action, actor, details_json, created_at)
                VALUES ('ALERT', ?, 'STATUS_UPDATED', ?, ?, ?)
                """,
                (
                    alert_id,
                    actor,
                    json.dumps(
                        {
                            "previous_status": existing["investigation_status"],
                            "new_status": status,
                            "assigned_to": new_assigned,
                            "resolution_outcome": new_resolution,
                            "note_added": bool(note and note.strip()),
                        }
                    ),
                    now_iso,
                ),
            )
            updated = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            return self._row_to_alert_dict(conn, updated)

    def add_alert_note(self, alert_id: str, author: str, note: str) -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            existing = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            if not existing:
                return None
            conn.execute(
                "INSERT INTO analyst_notes (alert_id, author, note, created_at) VALUES (?, ?, ?, ?)",
                (alert_id, author, note.strip(), now_iso),
            )
            conn.execute(
                """
                INSERT INTO audit_events (entity_type, entity_id, action, actor, details_json, created_at)
                VALUES ('ALERT', ?, 'NOTE_ADDED', ?, ?, ?)
                """,
                (alert_id, author, json.dumps({"note_preview": note.strip()[:80]}), now_iso),
            )
            return self._row_to_alert_dict(conn, existing)

    def record_dead_letter(self, raw_payload: Any, error_reason: str) -> int:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            cur = conn.execute(
                "INSERT INTO dead_letter_events (raw_payload_json, error_reason, received_at) VALUES (?, ?, ?)",
                (json.dumps(raw_payload, default=str), error_reason, now_iso),
            )
            return int(cur.lastrowid or 0)

    def list_dead_letters(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM dead_letter_events ORDER BY dlq_id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "dlq_id": r["dlq_id"],
                    "raw_payload": json.loads(r["raw_payload_json"]),
                    "error_reason": r["error_reason"],
                    "received_at": r["received_at"],
                }
                for r in rows
            ]

    def save_model_metadata(
        self, model_version: str, model_type: str, trained_at: str, feature_names: List[str], metrics: Dict[str, Any]
    ) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE model_metadata SET is_active = 0")
            conn.execute(
                """
                INSERT OR REPLACE INTO model_metadata (
                    model_version, model_type, trained_at, feature_names_json, metrics_json, is_active
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (model_version, model_type, trained_at, json.dumps(feature_names), json.dumps(metrics)),
            )

    def get_overview_aggregates(self) -> Dict[str, Any]:
        with self.connection() as conn:
            tx_stats = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_tx,
                    SUM(CASE WHEN risk_category = 'HIGH_RISK' THEN 1 ELSE 0 END) AS high_risk_tx,
                    SUM(CASE WHEN risk_category = 'REVIEW' THEN 1 ELSE 0 END) AS review_tx,
                    SUM(CASE WHEN risk_category = 'LOW_RISK' THEN 1 ELSE 0 END) AS low_risk_tx,
                    COALESCE(SUM(CASE WHEN risk_category IN ('HIGH_RISK', 'REVIEW') THEN transaction_amount ELSE 0 END), 0.0) AS flagged_value,
                    COALESCE(AVG(processing_latency_ms), 0.0) AS avg_latency_ms,
                    SUM(CASE WHEN fraud_label = 1 THEN 1 ELSE 0 END) AS labeled_fraud_tx
                FROM transactions
                """
            ).fetchone()

            alert_stats = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_alerts,
                    SUM(CASE WHEN investigation_status != 'RESOLVED' THEN 1 ELSE 0 END) AS open_alerts,
                    SUM(CASE WHEN resolution_outcome = 'CONFIRMED_FRAUD' THEN 1 ELSE 0 END) AS confirmed_fraud_alerts
                FROM alerts
                """
            ).fetchone()

            dlq_cnt = conn.execute("SELECT COUNT(*) AS cnt FROM dead_letter_events").fetchone()["cnt"]

            recent_series = conn.execute(
                """
                SELECT
                    substr(event_timestamp, 1, 16) AS minute_bucket,
                    COUNT(*) AS tx_count,
                    SUM(CASE WHEN risk_category = 'HIGH_RISK' THEN 1 ELSE 0 END) AS high_risk_count,
                    ROUND(SUM(transaction_amount), 2) AS total_amount,
                    ROUND(AVG(combined_score), 3) AS avg_risk_score
                FROM transactions
                GROUP BY minute_bucket
                ORDER BY minute_bucket DESC
                LIMIT 20
                """
            ).fetchall()

            return {
                "total_transactions": tx_stats["total_tx"] or 0,
                "high_risk_transactions": tx_stats["high_risk_tx"] or 0,
                "review_transactions": tx_stats["review_tx"] or 0,
                "low_risk_transactions": tx_stats["low_risk_tx"] or 0,
                "flagged_transaction_value": round(float(tx_stats["flagged_value"] or 0.0), 2),
                "avg_processing_latency_ms": round(float(tx_stats["avg_latency_ms"] or 0.0), 2),
                "labeled_fraud_transactions": tx_stats["labeled_fraud_tx"] or 0,
                "total_alerts": alert_stats["total_alerts"] or 0,
                "open_alerts": alert_stats["open_alerts"] or 0,
                "confirmed_fraud_count": (alert_stats["confirmed_fraud_alerts"] or 0) + (tx_stats["labeled_fraud_tx"] or 0),
                "failed_event_count": dlq_cnt or 0,
                "time_series": [dict(r) for r in reversed(recent_series)],
            }

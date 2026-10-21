import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.database.db import DatabaseManager


class AlertManager:
    """Manages live fraud alert generation, duplicate alert suppression with configurable cooldowns,
    severity classification, database persistence, and investigation workflow transitions.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        # Cooldown tracker: (account_id, signature_key) -> last_alert_datetime
        self._cooldown_tracker: Dict[Tuple[str, str], datetime] = {}
        self.suppressed_count: int = 0

    def evaluate_and_create_alert(
        self, scored_tx: Dict[str, Any], bypass_cooldown: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Evaluates whether `scored_tx` warrants an alert.
        Returns (alert_dict_or_None, was_suppressed_by_cooldown).
        """
        risk_category = scored_tx["risk_category"]
        combined_score = float(scored_tx["combined_score"])
        triggered_rules: List[str] = scored_tx.get("triggered_rules", [])

        if risk_category == "LOW_RISK" and len(triggered_rules) == 0:
            return None, False

        if combined_score < settings.threshold_review and len(triggered_rules) < 2:
            return None, False

        account_id = scored_tx["source_account_id"]
        rule_sig = "|".join(sorted([r.split(":")[0] for r in triggered_rules])) or risk_category
        cooldown_key = (account_id, rule_sig)

        now_dt = datetime.now(timezone.utc)
        try:
            event_dt = datetime.fromisoformat(scored_tx["event_timestamp"])
        except Exception:
            event_dt = now_dt

        # Duplicate alert suppression within configurable cooldown window
        cooldown_sec = settings.alert_cooldown_seconds
        if not bypass_cooldown and cooldown_sec > 0 and cooldown_key in self._cooldown_tracker:
            prev_dt = self._cooldown_tracker[cooldown_key]
            elapsed = abs((event_dt - prev_dt).total_seconds())
            # Suppress identical rule signature on the same account within cooldown window unless score is CRITICAL (>=0.88)
            if elapsed < cooldown_sec and combined_score < 0.88:
                self.suppressed_count += 1
                return None, True

        self._cooldown_tracker[cooldown_key] = event_dt

        if combined_score >= 0.85 or (risk_category == "HIGH_RISK" and len(triggered_rules) >= 2):
            severity = "CRITICAL"
        elif risk_category == "HIGH_RISK" or combined_score >= settings.threshold_high_risk:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        methods = []
        if float(scored_tx["ml_score"]) >= 0.55:
            methods.append("SUPERVISED_ML")
        if float(scored_tx["graph_score"]) >= 0.40:
            methods.append("GRAPH_INTELLIGENCE")
        if triggered_rules:
            methods.append("RULE_ENGINE")
        detection_method = " + ".join(methods) if methods else "HYBRID_SCORE_THRESHOLD"

        alert_id = f"ALT-{uuid.uuid4().hex[:10].upper()}"
        alert_record: Dict[str, Any] = {
            "alert_id": alert_id,
            "transaction_id": scored_tx["transaction_id"],
            "account_id": account_id,
            "merchant_id": scored_tx.get("merchant_id"),
            "transaction_amount": scored_tx["transaction_amount"],
            "currency": scored_tx.get("currency", "USD"),
            "detection_timestamp": now_dt.isoformat(),
            "risk_score": combined_score,
            "risk_percentage": scored_tx["risk_percentage"],
            "ml_score": scored_tx["ml_score"],
            "graph_score": scored_tx["graph_score"],
            "rule_score": scored_tx["rule_score"],
            "severity": severity,
            "risk_category": risk_category,
            "detection_method": detection_method,
            "triggered_rules": triggered_rules,
            "model_explanation": scored_tx.get("top_risk_factors", []),
            "graph_relationships": scored_tx.get("graph_explanations", []),
            "investigation_status": "OPEN",
            "assigned_to": None,
            "resolution_outcome": "UNRESOLVED",
            "is_demo": bool(scored_tx.get("is_demo")),
            "scenario_tag": scored_tx.get("scenario_tag"),
            "notes": [],
            "audit_history": [
                {
                    "event_id": 1,
                    "action": "ALERT_CREATED",
                    "actor": "system.detector",
                    "details": {"severity": severity, "risk_score": combined_score},
                    "created_at": now_dt.isoformat(),
                }
            ],
        }
        self.db.save_alert(alert_record)
        return alert_record, False

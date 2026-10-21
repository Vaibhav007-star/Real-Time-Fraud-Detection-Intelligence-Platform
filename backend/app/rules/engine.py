from typing import Dict, List, Tuple
from app.schemas.transaction import TransactionCreate


class FraudRuleEngine:
    """Configurable rule-based risk engine producing explainable rule triggers and normalized rule score."""

    def evaluate(
        self, tx: TransactionCreate, features: Dict[str, float]
    ) -> Tuple[float, List[str]]:
        triggered: List[str] = []
        rule_points = 0.0

        # Rule 1: Extreme transaction amount or spike vs account baseline
        if tx.transaction_amount >= 4500.0 or (
            features.get("amount_ratio_vs_avg", 1.0) >= 6.0 and tx.transaction_amount >= 800.0
        ):
            triggered.append(
                f"RULE_HIGH_AMOUNT_ANOMALY: Amount ${tx.transaction_amount:,.2f} exceeds baseline ratio ({features.get('amount_ratio_vs_avg', 1.0):.1f}x)."
            )
            rule_points += 0.38

        # Rule 2: Card testing pattern (multiple failed attempts followed by completion)
        if features.get("failed_then_success_pattern", 0.0) >= 1.0:
            fails = int(features.get("recent_failed_attempts_15m", 0))
            triggered.append(
                f"RULE_CARD_TESTING_SEQUENCE: {fails} declined/failed attempts in 15m followed by completed transaction."
            )
            rule_points += 0.48
        elif tx.transaction_status in ("DECLINED", "FAILED") and features.get("recent_failed_attempts_15m", 0.0) >= 1.0:
            triggered.append(
                "RULE_REPEATED_DECLINES: Consecutive declined authorization attempts detected."
            )
            rule_points += 0.32

        # Rule 3: Shared device cluster
        dev_shared = int(features.get("device_shared_account_count", 1))
        if dev_shared >= 3:
            triggered.append(
                f"RULE_SHARED_DEVICE_RING: Device '{tx.device_id}' is actively used by {dev_shared} distinct accounts."
            )
            rule_points += 0.42
        elif dev_shared == 2:
            triggered.append(
                f"RULE_MULTI_ACCOUNT_DEVICE: Device '{tx.device_id}' linked to 2 accounts."
            )
            rule_points += 0.22

        # Rule 4: Circular transfer ring
        if features.get("has_circular_transfer_path", 0.0) >= 1.0:
            triggered.append(
                "RULE_CIRCULAR_FUNDS_FLOW: Directed transfer cycle detected returning to originating account."
            )
            rule_points += 0.52

        # Rule 5: Impossible travel / rapid geographic shift
        if features.get("rapid_location_change", 0.0) >= 1.0:
            triggered.append(
                f"RULE_RAPID_GEO_SHIFT: Account transacted in '{tx.location}' within 10 minutes of a different region."
            )
            rule_points += 0.36

        # Rule 6: High-risk merchant + unfamiliar device
        if (
            features.get("is_high_risk_merchant_cat", 0.0) >= 1.0
            and (features.get("is_first_time_device", 0.0) >= 1.0 or tx.transaction_amount >= 1500.0)
        ):
            triggered.append(
                f"RULE_HIGH_RISK_MERCHANT_EXPOSURE: High-risk category '{tx.merchant_category}' with elevated amount or new device."
            )
            rule_points += 0.28

        # Rule 7: High velocity burst
        if features.get("tx_count_1m", 0.0) >= 3.0 or features.get("tx_count_5m", 0.0) >= 5.0:
            triggered.append(
                f"RULE_VELOCITY_SPIKE: {int(features.get('tx_count_5m', 0)) + 1} transactions within 5-minute window."
            )
            rule_points += 0.30

        normalized_rule_score = round(min(0.99, max(0.01, rule_points)), 4)
        return normalized_rule_score, triggered

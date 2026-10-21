import math
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.schemas.transaction import TransactionCreate

HIGH_RISK_CATEGORIES = {
    "CRYPTO_EXCHANGE",
    "LUXURY_JEWELRY",
    "HIGH_VALUE_GIFT_CARDS",
    "OFFSHORE_GAMING",
}

FEATURE_NAMES: List[str] = [
    "tx_amount_log",
    "tx_count_1m",
    "tx_count_5m",
    "tx_count_15m",
    "tx_count_60m",
    "tx_amount_sum_5m",
    "tx_amount_sum_60m",
    "amount_ratio_vs_avg",
    "amount_zscore_vs_account",
    "seconds_since_prev_tx",
    "is_unusually_large_amount",
    "rapid_location_change",
    "is_high_risk_merchant_cat",
    "is_first_time_device",
    "is_first_time_merchant",
    "velocity_burst_ratio",
    "recent_failed_attempts_15m",
    "failed_then_success_pattern",
    "device_shared_account_count",
    "ip_shared_account_count",
    "repeated_transfer_count",
    "has_circular_transfer_path",
    "local_neighborhood_risk",
    "entity_degree_spike",
]


class AccountRollingState:
    """Bounded rolling history for a single account."""

    def __init__(self, max_events: int = 250) -> None:
        self.events: Deque[Tuple[datetime, float, str, str, str, str]] = deque(maxlen=max_events)
        # tuple: (event_dt, amount, status, location, device_id, merchant_id)
        self.known_devices: Set[str] = set()
        self.known_merchants: Set[str] = set()
        self.total_completed_count: int = 0
        self.running_sum: float = 0.0
        self.running_sq_sum: float = 0.0


class RealTimeFeatureEngine:
    """Computes streaming velocity, behavioral anomaly, and network-integrated features.

    Strictly computes features using only historical events prior to the current transaction
    to prevent target/future leakage during both training and real-time inference.
    """

    def __init__(self, max_accounts: int = 5000, max_events_per_account: int = 250) -> None:
        self.max_accounts = max_accounts
        self.max_events_per_account = max_events_per_account
        self._account_states: Dict[str, AccountRollingState] = {}

    def compute_and_update(
        self, tx: TransactionCreate, graph_features: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        acc_id = tx.source_account_id
        if acc_id not in self._account_states:
            if len(self._account_states) >= self.max_accounts:
                oldest_key = next(iter(self._account_states))
                del self._account_states[oldest_key]
            self._account_states[acc_id] = AccountRollingState(self.max_events_per_account)

        state = self._account_states[acc_id]
        event_dt = datetime.fromisoformat(tx.timestamp)
        amount = float(tx.transaction_amount)
        merch_id = tx.merchant_id or "NONE"
        loc = tx.location or "UNKNOWN"

        # 1. Velocity calculations over rolling windows (1m, 5m, 15m, 60m) prior to current tx
        cnt_1m = 0
        cnt_5m = 0
        cnt_15m = 0
        cnt_60m = 0
        sum_5m = 0.0
        sum_60m = 0.0
        failed_15m = 0
        prev_dt: Optional[datetime] = None
        prev_loc: Optional[str] = None

        for hist_dt, hist_amt, hist_status, hist_loc, _, _ in state.events:
            delta_s = (event_dt - hist_dt).total_seconds()
            if delta_s < -1.0:
                # Out-of-order future event relative to current event; skip to avoid time-travel leakage
                continue
            abs_delta = max(0.0, delta_s)
            if abs_delta <= 3600.0:
                cnt_60m += 1
                sum_60m += hist_amt
                if abs_delta <= 900.0:
                    cnt_15m += 1
                    if hist_status in ("FAILED", "DECLINED"):
                        failed_15m += 1
                    if abs_delta <= 300.0:
                        cnt_5m += 1
                        sum_5m += hist_amt
                        if abs_delta <= 60.0:
                            cnt_1m += 1
            if prev_dt is None or hist_dt >= prev_dt:
                prev_dt = hist_dt
                prev_loc = hist_loc

        seconds_since_prev = (
            max(0.0, (event_dt - prev_dt).total_seconds()) if prev_dt is not None else 86400.0
        )

        # 2. Historical spending deviation
        if state.total_completed_count >= 1:
            hist_avg = state.running_sum / state.total_completed_count
            variance = max(
                25.0,
                (state.running_sq_sum / state.total_completed_count) - (hist_avg * hist_avg),
            )
            hist_std = math.sqrt(variance)
        else:
            hist_avg = 85.0
            hist_std = 60.0

        amount_ratio = amount / max(1.0, hist_avg)
        amount_zscore = (amount - hist_avg) / max(5.0, hist_std)
        is_unusually_large = 1.0 if (amount >= 2500.0 or (amount_ratio >= 4.5 and amount >= 500.0)) else 0.0

        # 3. Behavioral anomalies
        rapid_loc_change = (
            1.0
            if (prev_loc is not None and prev_loc != loc and seconds_since_prev <= 600.0)
            else 0.0
        )
        is_high_risk_cat = 1.0 if (tx.merchant_category or "").upper() in HIGH_RISK_CATEGORIES else 0.0
        is_first_dev = 1.0 if (len(state.known_devices) > 0 and tx.device_id not in state.known_devices) else 0.0
        is_first_merch = 1.0 if (len(state.known_merchants) > 0 and merch_id not in state.known_merchants) else 0.0

        avg_per_min_60m = max(0.05, cnt_60m / 60.0)
        velocity_burst_ratio = min(25.0, cnt_1m / avg_per_min_60m)
        failed_then_success = 1.0 if (failed_15m >= 2 and tx.transaction_status == "COMPLETED") else 0.0

        # 4. Merge graph features
        gf = graph_features or {}
        features: Dict[str, float] = {
            "tx_amount_log": round(math.log1p(amount), 4),
            "tx_count_1m": float(cnt_1m),
            "tx_count_5m": float(cnt_5m),
            "tx_count_15m": float(cnt_15m),
            "tx_count_60m": float(cnt_60m),
            "tx_amount_sum_5m": round(sum_5m, 2),
            "tx_amount_sum_60m": round(sum_60m, 2),
            "account_avg_amount": round(hist_avg, 2),
            "amount_ratio_vs_avg": round(min(50.0, amount_ratio), 4),
            "amount_zscore_vs_account": round(min(25.0, max(-5.0, amount_zscore)), 4),
            "seconds_since_prev_tx": round(min(86400.0, seconds_since_prev), 2),
            "is_unusually_large_amount": is_unusually_large,
            "rapid_location_change": rapid_loc_change,
            "is_high_risk_merchant_cat": is_high_risk_cat,
            "is_first_time_device": is_first_dev,
            "is_first_time_merchant": is_first_merch,
            "velocity_burst_ratio": round(velocity_burst_ratio, 4),
            "recent_failed_attempts_15m": float(failed_15m),
            "failed_then_success_pattern": failed_then_success,
            "device_shared_account_count": float(gf.get("device_shared_account_count", 1.0)),
            "ip_shared_account_count": float(gf.get("ip_shared_account_count", 1.0)),
            "repeated_transfer_count": float(gf.get("repeated_transfer_count", 0.0)),
            "has_circular_transfer_path": float(gf.get("has_circular_transfer_path", 0.0)),
            "local_neighborhood_risk": round(float(gf.get("local_neighborhood_risk", 0.05)), 4),
            "entity_degree_spike": round(float(gf.get("entity_degree_spike", 0.0)), 4),
        }

        # 5. Update rolling state AFTER feature extraction (preventing target/future leakage)
        state.events.append((event_dt, amount, tx.transaction_status, loc, tx.device_id, merch_id))
        state.known_devices.add(tx.device_id)
        state.known_merchants.add(merch_id)
        if tx.transaction_status == "COMPLETED":
            state.total_completed_count += 1
            state.running_sum += amount
            state.running_sq_sum += amount * amount

        return features

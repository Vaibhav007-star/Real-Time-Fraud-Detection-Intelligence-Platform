import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


NORMAL_MERCHANTS = [
    ("MERCH-AMZ-01", "ECOMMERCE"),
    ("MERCH-GROC-02", "GROCERY"),
    ("MERCH-UTIL-03", "UTILITIES"),
    ("MERCH-CAFE-04", "DINING"),
    ("MERCH-TRVL-05", "TRAVEL"),
    ("MERCH-STRM-06", "SUBSCRIPTION"),
]

HIGH_RISK_MERCHANTS = [
    ("MERCH-CRYP-91", "CRYPTO_EXCHANGE"),
    ("MERCH-LUX-92", "LUXURY_JEWELRY"),
    ("MERCH-GIFT-93", "HIGH_VALUE_GIFT_CARDS"),
    ("MERCH-OFFS-94", "OFFSHORE_GAMING"),
]

LOCATIONS = ["US-NY", "US-CA", "US-TX", "US-IL", "GB-LON", "DE-BER", "SG-SIN", "IN-DEL", "JP-TYO"]


class SyntheticTransactionGenerator:
    """Deterministic synthetic transaction and fraud scenario generator for local demonstration and testing.

    All generated transactions carry `is_demo=True` so the platform clearly distinguishes DEMO DATA.
    Ground-truth `fraud_label` is kept strictly for evaluation metrics and never exposed to inference features.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._counter = 0
        self.accounts = [f"ACC-{1000 + i}" for i in range(60)]
        self.devices = [f"DEV-{2000 + i}" for i in range(65)]
        self.ips = [f"subnet-10.24.{i // 4}.x" for i in range(65)]
        # Shared suspicious ring resources
        self.ring_device = "DEV-SHARED-RING-999"
        self.ring_ip = "subnet-185.220.101.x"
        self.ring_accounts = ["ACC-RING-01", "ACC-RING-02", "ACC-RING-03", "ACC-RING-04"]

    def reset_seed(self, seed: int) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._counter = 0

    def _next_id(self, prefix: str = "TX-DEMO") -> str:
        self._counter += 1
        token = f"{self.rng.getrandbits(32):08x}"
        return f"{prefix}-{self._counter:05d}-{token}"

    def generate_normal_transaction(self, base_time: Optional[datetime] = None) -> Dict[str, Any]:
        ts = base_time or datetime.now(timezone.utc)
        idx = self.rng.randrange(len(self.accounts))
        acc = self.accounts[idx]
        dev = self.devices[idx]
        ip = self.ips[idx]
        merch_id, merch_cat = self.rng.choice(NORMAL_MERCHANTS)
        # 8% of legitimate transactions are high-value executive travel or electronics purchases
        if self.rng.random() < 0.08:
            amount = round(self.rng.uniform(950.0, 4800.0), 2)
            merch_id, merch_cat = ("MERCH-TRVL-05", "TRAVEL") if self.rng.random() < 0.5 else ("MERCH-LUX-92", "LUXURY_JEWELRY")
            if self.rng.random() < 0.35:
                dev = f"DEV-CORP-TABLET-{idx % 12}"
        else:
            amount = round(self.rng.lognormvariate(3.6, 0.65), 2)
            amount = max(4.50, min(amount, 650.00))
        loc = LOCATIONS[idx % 4]

        return {
            "transaction_id": self._next_id("TX-NORM"),
            "timestamp": ts.isoformat(),
            "source_account_id": acc,
            "destination_account_id": None,
            "merchant_id": merch_id,
            "merchant_category": merch_cat,
            "device_id": dev,
            "ip_address": ip,
            "transaction_amount": amount,
            "currency": "USD",
            "transaction_type": "PURCHASE",
            "location": loc,
            "transaction_status": "COMPLETED",
            "fraud_label": 0,
            "is_demo": True,
            "scenario_tag": "normal_baseline",
        }

    def generate_stream_batch(
        self, count: int = 1, fraud_rate: float = 0.18, base_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        now = base_time or datetime.now(timezone.utc)
        for i in range(count):
            event_time = now + timedelta(milliseconds=i * 150)
            if self.rng.random() < fraud_rate:
                scenario = self.rng.choice(
                    [
                        "shared_device_ring",
                        "account_takeover_high_value",
                        "circular_money_mule",
                        "card_testing_burst",
                        "impossible_travel",
                    ]
                )
                scenario_events = self.generate_scenario(scenario, base_time=event_time)
                events.extend(scenario_events)
            else:
                events.append(self.generate_normal_transaction(base_time=event_time))
        return events

    def generate_scenario(
        self, scenario_name: str, base_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        now = base_time or datetime.now(timezone.utc)
        name = scenario_name.lower().strip()

        if name == "shared_device_ring":
            # Multiple distinct accounts transacting rapidly through the exact same device & IP subnet
            out: List[Dict[str, Any]] = []
            merch_id, merch_cat = HIGH_RISK_MERCHANTS[0]
            for idx, acc in enumerate(self.ring_accounts):
                t = now + timedelta(seconds=idx * 4)
                out.append(
                    {
                        "transaction_id": self._next_id("TX-RING"),
                        "timestamp": t.isoformat(),
                        "source_account_id": acc,
                        "destination_account_id": "ACC-MULE-HUB-88",
                        "merchant_id": merch_id,
                        "merchant_category": merch_cat,
                        "device_id": self.ring_device,
                        "ip_address": self.ring_ip,
                        "transaction_amount": round(2850.0 + idx * 620.0, 2),
                        "currency": "USD",
                        "transaction_type": "TRANSFER",
                        "location": "SG-SIN",
                        "transaction_status": "COMPLETED",
                        "fraud_label": 1,
                        "is_demo": True,
                        "scenario_tag": "DEMO:shared_device_ring",
                    }
                )
            return out

        if name == "circular_money_mule":
            # Circular transfer ring: ACC-MULE-A -> ACC-MULE-B -> ACC-MULE-C -> ACC-MULE-A
            chain = [("ACC-MULE-A", "ACC-MULE-B"), ("ACC-MULE-B", "ACC-MULE-C"), ("ACC-MULE-C", "ACC-MULE-A")]
            out = []
            for idx, (src, dst) in enumerate(chain):
                t = now + timedelta(seconds=idx * 5)
                out.append(
                    {
                        "transaction_id": self._next_id("TX-CIRC"),
                        "timestamp": t.isoformat(),
                        "source_account_id": src,
                        "destination_account_id": dst,
                        "merchant_id": "MERCH-CRYP-91",
                        "merchant_category": "CRYPTO_EXCHANGE",
                        "device_id": f"DEV-MULE-{idx + 1}",
                        "ip_address": "subnet-185.220.102.x",
                        "transaction_amount": round(4900.0 - idx * 120.0, 2),
                        "currency": "USD",
                        "transaction_type": "TRANSFER",
                        "location": "GB-LON",
                        "transaction_status": "COMPLETED",
                        "fraud_label": 1,
                        "is_demo": True,
                        "scenario_tag": "DEMO:circular_money_mule",
                    }
                )
            return out

        if name == "card_testing_burst":
            # Multiple rapid failed attempts followed by a large high-risk purchase
            acc = "ACC-VICTIM-104"
            dev = "DEV-UNFAMILIAR-777"
            ip = "subnet-91.214.44.x"
            out = []
            for idx in range(3):
                t = now + timedelta(seconds=idx * 2)
                out.append(
                    {
                        "transaction_id": self._next_id("TX-TEST-FAIL"),
                        "timestamp": t.isoformat(),
                        "source_account_id": acc,
                        "destination_account_id": None,
                        "merchant_id": "MERCH-GIFT-93",
                        "merchant_category": "HIGH_VALUE_GIFT_CARDS",
                        "device_id": dev,
                        "ip_address": ip,
                        "transaction_amount": round(1.50 + idx * 0.75, 2),
                        "currency": "USD",
                        "transaction_type": "CARD_NOT_PRESENT",
                        "location": "DE-BER",
                        "transaction_status": "DECLINED",
                        "fraud_label": 1,
                        "is_demo": True,
                        "scenario_tag": "DEMO:card_testing_burst",
                    }
                )
            out.append(
                {
                    "transaction_id": self._next_id("TX-TEST-HIT"),
                    "timestamp": (now + timedelta(seconds=8)).isoformat(),
                    "source_account_id": acc,
                    "destination_account_id": None,
                    "merchant_id": "MERCH-LUX-92",
                    "merchant_category": "LUXURY_JEWELRY",
                    "device_id": dev,
                    "ip_address": ip,
                    "transaction_amount": 6450.00,
                    "currency": "USD",
                    "transaction_type": "CARD_NOT_PRESENT",
                    "location": "DE-BER",
                    "transaction_status": "COMPLETED",
                    "fraud_label": 1,
                    "is_demo": True,
                    "scenario_tag": "DEMO:card_testing_burst",
                }
            )
            return out

        if name == "impossible_travel":
            acc = "ACC-EXEC-209"
            out = [
                {
                    "transaction_id": self._next_id("TX-TRVL-1"),
                    "timestamp": now.isoformat(),
                    "source_account_id": acc,
                    "destination_account_id": None,
                    "merchant_id": "MERCH-CAFE-04",
                    "merchant_category": "DINING",
                    "device_id": "DEV-EXEC-209",
                    "ip_address": "subnet-10.24.2.x",
                    "transaction_amount": 42.00,
                    "currency": "USD",
                    "transaction_type": "PURCHASE",
                    "location": "US-NY",
                    "transaction_status": "COMPLETED",
                    "fraud_label": 0,
                    "is_demo": True,
                    "scenario_tag": "DEMO:impossible_travel",
                },
                {
                    "transaction_id": self._next_id("TX-TRVL-2"),
                    "timestamp": (now + timedelta(seconds=35)).isoformat(),
                    "source_account_id": acc,
                    "destination_account_id": "ACC-OFFSHORE-99",
                    "merchant_id": "MERCH-OFFS-94",
                    "merchant_category": "OFFSHORE_GAMING",
                    "device_id": "DEV-FOREIGN-808",
                    "ip_address": "subnet-203.0.113.x",
                    "transaction_amount": 7800.00,
                    "currency": "USD",
                    "transaction_type": "WIRE",
                    "location": "JP-TYO",
                    "transaction_status": "COMPLETED",
                    "fraud_label": 1,
                    "is_demo": True,
                    "scenario_tag": "DEMO:impossible_travel",
                },
            ]
            return out

        # Default: account_takeover_high_value (includes both high-value wire & stealth mid-value ATO)
        acc = self.rng.choice(self.accounts[:20])
        is_stealth = self.rng.random() < 0.35
        return [
            {
                "transaction_id": self._next_id("TX-ATO"),
                "timestamp": now.isoformat(),
                "source_account_id": acc,
                "destination_account_id": "ACC-DROP-707",
                "merchant_id": "MERCH-TRVL-05" if is_stealth else "MERCH-CRYP-91",
                "merchant_category": "TRAVEL" if is_stealth else "CRYPTO_EXCHANGE",
                "device_id": self.ring_device if not is_stealth else f"DEV-SHARED-STEALTH-{self.rng.randint(1, 3)}",
                "ip_address": self.ring_ip,
                "transaction_amount": round(self.rng.uniform(210.0, 790.0) if is_stealth else self.rng.uniform(3800.0, 11500.0), 2),
                "currency": "USD",
                "transaction_type": "PURCHASE" if is_stealth else "WIRE",
                "location": "US-NY" if is_stealth else "SG-SIN",
                "transaction_status": "COMPLETED",
                "fraud_label": 1,
                "is_demo": True,
                "scenario_tag": "DEMO:account_takeover_high_value",
            }
        ]

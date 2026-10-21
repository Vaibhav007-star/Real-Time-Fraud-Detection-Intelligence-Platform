#!/usr/bin/env python3
"""Generates sample CSV datasets in `data/sample/`:
1. `creditcard_sample.csv`: Mirrors the public Credit Card Fraud dataset schema (`Time, V1..V5, Amount, Class`)
   to demonstrate dataset upload, schema validation, class distribution analysis, and clearly labeled synthetic graph entity mapping.
2. `synthetic_stream_replay.csv`: Full canonical transaction dataset with native account, device, IP, and merchant relationships.
"""
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ingestion.generator import SyntheticTransactionGenerator


def main() -> None:
    sample_dir = ROOT / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate creditcard_sample.csv (public schema without native account/device IDs)
    rng = random.Random(42)
    cc_path = sample_dir / "creditcard_sample.csv"
    with open(cc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "V1", "V2", "V3", "V4", "V5", "Amount", "Class"])
        for i in range(120):
            is_fraud = 1 if rng.random() < 0.12 else 0
            time_val = i * 12.5
            v1 = round(rng.gauss(-2.8 if is_fraud else 0.1, 1.1), 4)
            v2 = round(rng.gauss(2.4 if is_fraud else -0.1, 1.0), 4)
            v3 = round(rng.gauss(-3.5 if is_fraud else 0.2, 1.2), 4)
            v4 = round(rng.gauss(3.1 if is_fraud else 0.0, 0.9), 4)
            v5 = round(rng.gauss(-1.9 if is_fraud else 0.05, 1.0), 4)
            amt = round(rng.uniform(1800.0, 6200.0) if is_fraud else rng.lognormvariate(3.4, 0.6), 2)
            writer.writerow([time_val, v1, v2, v3, v4, v5, amt, is_fraud])

    # 2. Generate synthetic_stream_replay.csv (canonical transaction schema)
    gen = SyntheticTransactionGenerator(seed=42)
    events = gen.generate_stream_batch(count=80, fraud_rate=0.16)
    replay_path = sample_dir / "synthetic_stream_replay.csv"
    fieldnames = [
        "transaction_id",
        "timestamp",
        "source_account_id",
        "destination_account_id",
        "merchant_id",
        "merchant_category",
        "device_id",
        "ip_address",
        "transaction_amount",
        "currency",
        "transaction_type",
        "location",
        "transaction_status",
        "fraud_label",
        "is_demo",
        "scenario_tag",
    ]
    with open(replay_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ev in events:
            writer.writerow({k: ev.get(k, "") for k in fieldnames})

    print(f"Generated {cc_path.name} (120 rows) and {replay_path.name} ({len(events)} rows).")


if __name__ == "__main__":
    main()

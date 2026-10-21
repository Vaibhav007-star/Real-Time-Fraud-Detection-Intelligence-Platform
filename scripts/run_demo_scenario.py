#!/usr/bin/env python3
"""CLI utility to trigger a demonstration fraud scenario against the local orchestrator or running API."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services.orchestrator import FraudPlatformOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic fraud detection scenario.")
    parser.add_argument(
        "--scenario",
        default="shared_device_ring",
        choices=[
            "shared_device_ring",
            "circular_money_mule",
            "card_testing_burst",
            "impossible_travel",
            "account_takeover_high_value",
        ],
    )
    args = parser.parse_args()

    orch = FraudPlatformOrchestrator()
    events = orch.generator.generate_scenario(args.scenario)
    print(f"Injecting scenario '{args.scenario}' ({len(events)} events)...")
    for ev in events:
        res = orch.process_transaction_sync(ev)
        tx = res["transaction"]
        alert = res.get("alert")
        print(
            f"  -> TX {tx['transaction_id']} | Amount: ${tx['transaction_amount']:,.2f} | "
            f"ML: {tx['ml_score']:.2f}, Graph: {tx['graph_score']:.2f}, Rule: {tx['rule_score']:.2f} => "
            f"Combined: {tx['combined_score']:.2f} ({tx['risk_category']})"
            + (f" [ALERT: {alert['alert_id']} ({alert['severity']})]" if alert else "")
        )


if __name__ == "__main__":
    main()

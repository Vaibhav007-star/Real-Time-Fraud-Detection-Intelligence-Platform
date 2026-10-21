import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from app.ingestion.csv_loader import CSVDatasetInspector
from app.services.orchestrator import FraudPlatformOrchestrator


class TestDataPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.orch = FraudPlatformOrchestrator(db_path=":memory:")

    def test_valid_transaction_processing(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "transaction_id": "TX-VALID-001",
            "timestamp": now_iso,
            "source_account_id": "ACC-101",
            "merchant_id": "MERCH-01",
            "merchant_category": "ECOMMERCE",
            "device_id": "DEV-101",
            "ip_address": "subnet-10.0.1.x",
            "transaction_amount": 125.50,
            "currency": "USD",
            "transaction_type": "PURCHASE",
            "location": "US-NY",
            "transaction_status": "COMPLETED",
        }
        res = self.orch.process_transaction_sync(payload)
        self.assertEqual(res["status"], "PROCESSED")
        tx = res["transaction"]
        self.assertEqual(tx["transaction_id"], "TX-VALID-001")
        self.assertIn(tx["risk_category"], ("LOW_RISK", "REVIEW", "HIGH_RISK"))
        self.assertNotEqual(tx["event_timestamp"], "")
        self.assertNotEqual(tx["ingestion_timestamp"], "")

    def test_invalid_transaction_rejection_and_dlq(self) -> None:
        # Missing required fields
        res1 = self.orch.process_transaction_sync({"transaction_id": "TX-BAD-1"})
        self.assertEqual(res1["status"], "REJECTED")
        self.assertIsNotNone(res1["dlq_id"])

        # Negative transaction amount
        res2 = self.orch.process_transaction_sync(
            {
                "transaction_id": "TX-BAD-2",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_account_id": "ACC-101",
                "device_id": "DEV-101",
                "ip_address": "subnet-10.0.1.x",
                "transaction_amount": -45.0,
            }
        )
        self.assertEqual(res2["status"], "REJECTED")
        dlq_items = self.orch.db.list_dead_letters()
        self.assertEqual(len(dlq_items), 2)

    def test_duplicate_event_idempotency(self) -> None:
        payload = {
            "transaction_id": "TX-DUP-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_account_id": "ACC-202",
            "device_id": "DEV-202",
            "ip_address": "subnet-10.0.2.x",
            "transaction_amount": 85.00,
        }
        first = self.orch.process_transaction_sync(payload)
        self.assertEqual(first["status"], "PROCESSED")

        second = self.orch.process_transaction_sync(payload)
        self.assertEqual(second["status"], "DUPLICATE_IDEMPOTENT")
        self.assertEqual(second["transaction"]["transaction_id"], "TX-DUP-001")
        self.assertEqual(self.orch.metrics.duplicate_events_count, 1)

    def test_late_and_out_of_order_events(self) -> None:
        now = datetime.now(timezone.utc)
        # Process a current transaction to advance watermark
        self.orch.process_transaction_sync(
            {
                "transaction_id": "TX-NOW-01",
                "timestamp": now.isoformat(),
                "source_account_id": "ACC-301",
                "device_id": "DEV-301",
                "ip_address": "subnet-10.0.3.x",
                "transaction_amount": 50.0,
            }
        )
        # Process an out-of-order transaction from 25 minutes earlier
        late_ts = (now - timedelta(minutes=25)).isoformat()
        res_late = self.orch.process_transaction_sync(
            {
                "transaction_id": "TX-LATE-02",
                "timestamp": late_ts,
                "source_account_id": "ACC-301",
                "device_id": "DEV-301",
                "ip_address": "subnet-10.0.3.x",
                "transaction_amount": 75.0,
            }
        )
        self.assertEqual(res_late["status"], "PROCESSED")
        self.assertTrue(res_late["transaction"]["is_late_event"])
        self.assertGreater(res_late["transaction"]["late_by_seconds"], 1000.0)

    def test_streaming_start_pause_and_stop(self) -> None:
        async def _run():
            status1 = await self.orch.start_stream(tps=10.0, fraud_rate=0.2, seed=42)
            self.assertTrue(status1["running"])
            await asyncio.sleep(0.25)
            paused = self.orch.pause_or_resume_stream(True)
            self.assertTrue(paused["paused"])
            stopped = await self.orch.stop_stream()
            self.assertFalse(stopped["running"])

        asyncio.run(_run())
        agg = self.orch.db.get_overview_aggregates()
        self.assertGreaterEqual(agg["total_transactions"], 1)

    def test_csv_dataset_validation_and_provenance(self) -> None:
        csv_content = b"Time,V1,V2,Amount,Class\n0,-1.35,0.89,149.62,0\n12,-3.20,2.95,2450.00,1\n"
        summary, records = CSVDatasetInspector.analyze_and_convert(
            csv_bytes=csv_content, filename="creditcard_mini.csv", inject_synthetic_graph=True
        )
        self.assertEqual(summary["total_rows"], 2)
        self.assertTrue(summary["class_distribution"]["labeled"])
        self.assertEqual(summary["class_distribution"]["fraud_1"], 1)
        self.assertIn("source_account_id", summary["simulated_graph_fields"])
        self.assertEqual(len(records), 2)

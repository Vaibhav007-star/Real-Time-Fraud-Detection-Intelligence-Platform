import unittest
from datetime import datetime, timedelta, timezone

from app.graph.engine import GraphFraudIntelligenceEngine
from app.schemas.transaction import TransactionCreate


class TestGraphAnalyticsEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = GraphFraudIntelligenceEngine(max_nodes=200, lookback_seconds=3600, max_traversal_depth=3)

    def test_empty_and_incomplete_graph_behavior(self) -> None:
        sub = self.graph.get_entity_neighborhood(center_id="NON-EXISTENT")
        self.assertEqual(sub["nodes"], [])
        self.assertEqual(sub["edges"], [])

    def test_shared_device_cluster_detection(self) -> None:
        now = datetime.now(timezone.utc)
        for idx, acc in enumerate(["ACC-A1", "ACC-A2", "ACC-A3"]):
            tx = TransactionCreate(
                transaction_id=f"TX-G-{idx}",
                timestamp=(now + timedelta(seconds=idx * 5)).isoformat(),
                source_account_id=acc,
                device_id="DEV-SHARED-X",
                ip_address="subnet-192.0.2.x",
                transaction_amount=500.0,
            )
            gf, gscore, explanations = self.graph.analyze_and_record_transaction(tx)
        self.assertEqual(gf["device_shared_account_count"], 3.0)
        self.assertGreater(gscore, 0.30)
        self.assertTrue(any("DEV-SHARED-X" in exp for exp in explanations))

    def test_circular_transfer_detection_and_bounded_traversal(self) -> None:
        now = datetime.now(timezone.utc)
        hops = [("ACC-C1", "ACC-C2"), ("ACC-C2", "ACC-C3"), ("ACC-C3", "ACC-C1")]
        last_gf = {}
        last_explanations = []
        for idx, (src, dst) in enumerate(hops):
            tx = TransactionCreate(
                transaction_id=f"TX-CYCLE-{idx}",
                timestamp=(now + timedelta(seconds=idx * 10)).isoformat(),
                source_account_id=src,
                destination_account_id=dst,
                device_id=f"DEV-C-{idx}",
                ip_address="subnet-198.51.100.x",
                transaction_amount=3000.0,
                transaction_type="TRANSFER",
            )
            last_gf, _, last_explanations = self.graph.analyze_and_record_transaction(tx)

        self.assertEqual(last_gf["has_circular_transfer_path"], 1.0)
        self.assertTrue(any("Circular transfer ring" in e for e in last_explanations))

        sub = self.graph.get_entity_neighborhood(center_id="ACC-C1", max_depth=2)
        self.assertGreaterEqual(len(sub["nodes"]), 3)
        self.assertGreaterEqual(len(sub["edges"]), 2)

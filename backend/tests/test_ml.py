import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.ml.pipeline import FraudMLPipeline
from app.services.orchestrator import FraudPlatformOrchestrator


class TestMachineLearningEngine(unittest.TestCase):
    def test_training_and_reproducible_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = FraudMLPipeline(model_dir=Path(tmpdir))
            rep1 = p1.train_and_evaluate(seed=99, num_streams=300)
            self.assertTrue(p1.model_loaded)
            self.assertIn("improved_model_metrics", rep1)
            self.assertIn("baseline_model_metrics", rep1)
            imp = rep1["improved_model_metrics"]
            self.assertTrue(imp["available"])
            self.assertGreater(imp["pr_auc"], 0.70)
            self.assertGreater(imp["f1_score"], 0.65)
            self.assertIn("confusion_matrix", imp)

            # Re-load artifact into fresh pipeline instance
            p2 = FraudMLPipeline(model_dir=Path(tmpdir))
            self.assertTrue(p2.model_loaded)
            self.assertEqual(p2.model_version, p1.model_version)

    def test_missing_model_fallback_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_pipe = FraudMLPipeline(model_dir=Path(tmpdir))
            self.assertFalse(empty_pipe.model_loaded)
            res = empty_pipe.score_features(
                {
                    "tx_amount_log": 8.5,
                    "amount_ratio_vs_avg": 9.0,
                    "is_unusually_large_amount": 1.0,
                    "device_shared_account_count": 4.0,
                    "has_circular_transfer_path": 1.0,
                }
            )
            self.assertEqual(res["scoring_method"], "unsupervised_anomaly_fallback")
            self.assertEqual(res["scoring_status"], "FALLBACK_ANOMALY_SCORER")
            self.assertGreater(res["ml_score"], 0.5)
            self.assertTrue(len(res["warnings"]) > 0)

    def test_no_target_leakage_during_inference(self) -> None:
        orch1 = FraudPlatformOrchestrator(db_path=":memory:")
        orch2 = FraudPlatformOrchestrator(db_path=":memory:")
        ts = datetime.now(timezone.utc).isoformat()
        base_tx = {
            "transaction_id": "TX-LEAK-TEST",
            "timestamp": ts,
            "source_account_id": "ACC-500",
            "device_id": "DEV-500",
            "ip_address": "subnet-10.5.0.x",
            "transaction_amount": 1450.0,
            "currency": "USD",
            "transaction_type": "PURCHASE",
        }
        r_label_0 = orch1.process_transaction_sync({**base_tx, "fraud_label": 0})["transaction"]
        r_label_1 = orch2.process_transaction_sync({**base_tx, "fraud_label": 1})["transaction"]
        # Scoring must be 100% identical regardless of ground-truth fraud_label
        self.assertEqual(r_label_0["ml_score"], r_label_1["ml_score"])
        self.assertEqual(r_label_0["combined_score"], r_label_1["combined_score"])

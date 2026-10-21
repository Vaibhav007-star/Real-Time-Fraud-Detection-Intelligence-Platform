import unittest
from pathlib import Path

from app.ml.kaggle_benchmark import KaggleBenchmarkEngine
from app.main import create_app
from fastapi.testclient import TestClient


class TestKaggleRealDataIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = KaggleBenchmarkEngine()

    def test_kaggle_raw_dataset_available(self):
        self.assertTrue(
            self.engine.is_raw_data_available(),
            "Real Kaggle dataset (creditcard.csv) should be downloaded and available in data/kaggle/",
        )

    def test_kaggle_benchmark_sample_creation(self):
        sample_path = self.engine.prepare_benchmark_sample(n_total=200, seed=42)
        self.assertTrue(sample_path.exists())
        self.assertGreater(sample_path.stat().st_size, 1000)

    def test_kaggle_real_sample_generation_for_stream(self):
        samples = self.engine.get_real_sample_transactions(count=10, fraud_ratio=0.3)
        self.assertEqual(len(samples), 10)
        self.assertTrue(any(s["fraud_label"] == 1 for s in samples))
        self.assertTrue(any(s["fraud_label"] == 0 for s in samples))
        self.assertIn("KAG-", samples[0]["transaction_id"])
        self.assertEqual(samples[0]["currency"], "EUR")

    def test_kaggle_benchmark_cached_report_valid(self):
        report = self.engine.get_or_run_benchmark()
        self.assertIn("dataset_provenance", report)
        self.assertIn("models", report)
        self.assertIn("xgboost", report["models"])
        self.assertIn("logistic_regression", report["models"])
        self.assertIn("random_forest", report["models"])

        # Validate that XGBoost and Random Forest achieve strong PR-AUC on real data
        xgb_m = report["models"]["xgboost"]
        self.assertGreater(xgb_m["pr_auc"], 0.70)
        self.assertGreater(xgb_m["roc_auc"], 0.95)
        self.assertIn("financial_roi", xgb_m)
        self.assertGreater(xgb_m["financial_roi"]["fraud_amount_prevented_usd"], 0)

    def test_api_kaggle_endpoints(self):
        app = create_app(db_path=":memory:", bootstrap_demo=False)
        client = TestClient(app)

        # 1. Test benchmark API endpoint
        res = client.get("/api/model/kaggle/benchmark")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("dataset_provenance", data)
        self.assertIn("models", data)

        # 2. Test Kaggle stream burst replay endpoint
        burst_res = client.post("/api/stream/kaggle/burst", json={"count": 5, "fraud_ratio": 0.4})
        self.assertEqual(burst_res.status_code, 200)
        burst_data = burst_res.json()
        self.assertEqual(burst_data["events_injected"], 5)
        self.assertGreaterEqual(len(burst_data["transactions_scored"]), 1)


if __name__ == "__main__":
    unittest.main()

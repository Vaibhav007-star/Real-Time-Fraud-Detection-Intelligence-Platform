import unittest
from app.core.config import settings
from app.scoring.hybrid import HybridRiskScoringEngine


class TestHybridRiskScoring(unittest.TestCase):
    def setUp(self) -> None:
        self.scorer = HybridRiskScoringEngine()
        settings.update_scoring_config(0.45, 0.30, 0.25, 0.45, 0.72, 120)

    def test_risk_category_assignment(self) -> None:
        low = self.scorer.compute_hybrid_score(0.10, 0.05, 0.02, [], [])
        self.assertEqual(low["risk_category"], "LOW_RISK")

        rev = self.scorer.compute_hybrid_score(0.62, 0.48, 0.40, ["RULE_1"], [])
        self.assertEqual(rev["risk_category"], "REVIEW")

        high = self.scorer.compute_hybrid_score(0.92, 0.75, 0.88, ["RULE_1", "RULE_2"], ["Shared device"])
        self.assertEqual(high["risk_category"], "HIGH_RISK")
        self.assertGreaterEqual(high["combined_score"], 0.72)

    def test_missing_signal_handling(self) -> None:
        res = self.scorer.compute_hybrid_score(None, 0.80, 0.85, ["RULE_1"], ["Graph cluster"])
        self.assertEqual(res["risk_category"], "HIGH_RISK")
        self.assertTrue(any("ML score unavailable" in w for w in res["warnings"]))

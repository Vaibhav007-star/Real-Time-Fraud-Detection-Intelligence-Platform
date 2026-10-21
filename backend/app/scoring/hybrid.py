from typing import Any, Dict, List, Optional
from app.core.config import settings


class HybridRiskScoringEngine:
    """Combines Supervised ML Score, Graph-Based Risk Score, and Rule-Based Risk Score.

    Applies configurable weights (`weight_ml_score`, `weight_graph_score`, `weight_rule_score`)
    and accounts for signal correlation so shared underlying evidence (e.g., a shared device
    counted in both graph_score and rule_score) does not artificially saturate without bound.
    """

    def compute_hybrid_score(
        self,
        ml_score: Optional[float],
        graph_score: Optional[float],
        rule_score: Optional[float],
        triggered_rules: List[str],
        graph_explanations: List[str],
    ) -> Dict[str, Any]:
        warnings: List[str] = []

        # Handle missing signals gracefully by re-normalizing available weights
        available_signals: List[Tuple[str, float, float]] = []
        if ml_score is not None:
            available_signals.append(("ml", float(ml_score), settings.weight_ml_score))
        else:
            warnings.append("ML score unavailable; re-weighting across Graph and Rule signals.")

        if graph_score is not None:
            available_signals.append(("graph", float(graph_score), settings.weight_graph_score))
        else:
            warnings.append("Graph score unavailable; re-weighting across remaining signals.")

        if rule_score is not None:
            available_signals.append(("rule", float(rule_score), settings.weight_rule_score))
        else:
            warnings.append("Rule score unavailable; re-weighting across remaining signals.")

        if not available_signals:
            return {
                "combined_score": 0.0,
                "risk_percentage": 0.0,
                "risk_category": "LOW_RISK",
                "warnings": ["All scoring signals were missing."],
            }

        total_w = sum(w for _, _, w in available_signals)
        weighted_linear = sum((val * (w / total_w)) for _, val, w in available_signals)

        # Correlation adjustment: if both graph and rule signals triggered on the same topology
        # (e.g., shared device or circular transfer), dampen linear double-counting by 8% while
        # preserving high-confidence multi-modal agreement when ML also agrees.
        g_val = float(graph_score or 0.0)
        r_val = float(rule_score or 0.0)
        m_val = float(ml_score or 0.0)

        overlap_dampening = 0.0
        if g_val >= 0.45 and r_val >= 0.45:
            overlap_dampening = 0.06 * min(g_val, r_val)

        # High-confidence synergy boost when at least two independent pillars strongly flag fraud
        synergy_boost = 0.0
        strong_pillars = sum(1 for s in (m_val, g_val, r_val) if s >= 0.65)
        if strong_pillars >= 2:
            synergy_boost = 0.12

        combined = min(0.995, max(0.005, weighted_linear - overlap_dampening + synergy_boost))
        combined = round(combined, 4)

        if combined >= settings.threshold_high_risk:
            category = "HIGH_RISK"
        elif combined >= settings.threshold_review:
            category = "REVIEW"
        else:
            category = "LOW_RISK"

        return {
            "combined_score": combined,
            "risk_percentage": round(combined * 100.0, 2),
            "risk_category": category,
            "weights_applied": {
                "ml": settings.weight_ml_score,
                "graph": settings.weight_graph_score,
                "rule": settings.weight_rule_score,
            },
            "thresholds_applied": {
                "review": settings.threshold_review,
                "high_risk": settings.threshold_high_risk,
            },
            "warnings": warnings,
        }

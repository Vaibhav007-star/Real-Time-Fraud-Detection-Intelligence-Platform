#!/usr/bin/env python3
"""Trains the supervised fraud detection model on chronological synthetic stream data and saves artifacts to `models/`."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.pipeline import FraudMLPipeline


def main() -> None:
    pipeline = FraudMLPipeline()
    report = pipeline.train_and_evaluate(seed=42, num_streams=700)
    imp = report["improved_model_metrics"]
    base = report["baseline_model_metrics"]
    print(f"Model trained: {report['model_version']}")
    print(f"Baseline  -> PR-AUC: {base['pr_auc']:.4f} | F1: {base['f1_score']:.4f} | Recall: {base['recall']:.4f}")
    print(f"Improved  -> PR-AUC: {imp['pr_auc']:.4f} | F1: {imp['f1_score']:.4f} | Recall: {imp['recall']:.4f} | Precision@K: {imp['precision_at_k']:.4f}")


if __name__ == "__main__":
    main()

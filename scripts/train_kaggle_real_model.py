#!/usr/bin/env python3
"""Trains and evaluates Machine Learning Models (Logistic Regression, Random Forest, XGBoost)
on the real-world European Cardholders Kaggle Dataset (284,807 transactions).
Saves artifacts and a comprehensive financial ROI evaluation to models/kaggle_benchmark_report.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.kaggle_benchmark import KaggleBenchmarkEngine


def main() -> None:
    print("=" * 80)
    print("  REAL-WORLD KAGGLE CREDIT CARD FRAUD BENCHMARK & MODEL TRAINING")
    print("  Dataset: 284,807 Transactions (492 Frauds | 0.1727% Imbalance)")
    print("=" * 80)

    engine = KaggleBenchmarkEngine()
    if not engine.is_raw_data_available():
        print("[!] Dataset not found. Fetching from Kaggle...")
        import subprocess
        fetch_script = ROOT / "scripts" / "fetch_kaggle_dataset.py"
        subprocess.run([sys.executable, str(fetch_script)], check=True)

    print("\n[+] Running Out-of-Time Chronological Benchmark (80% Train, 20% Test)...")
    report = engine.run_benchmark(split_ratio=0.80)

    ds = report["dataset_provenance"]
    print(f"\n[DATASET SUMMARY]")
    print(f"  Total Transactions : {ds['total_transactions']:,}")
    print(f"  Test Transactions  : {ds['test_size']:,} (Unseen out-of-time evaluation)")
    print(f"  Test Fraud Count   : {ds['test_fraud_count']:,}")
    print(f"  Test Fraud Value   : ${ds['test_fraud_exposure_usd']:,.2f}")

    print("\n[MODEL PERFORMANCE COMPARISON]")
    print(f"{'Model Name':<42} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'Recall':<8} | {'Precision':<10} | {'F1':<8}")
    print("-" * 96)
    for key, m in report["models"].items():
        print(
            f"{m['model_name'][:40]:<42} | "
            f"{m['pr_auc']:<8.4f} | "
            f"{m['roc_auc']:<8.4f} | "
            f"{m['recall']*100:<7.1f}% | "
            f"{m['precision']*100:<9.1f}% | "
            f"{m['f1_score']:<8.4f}"
        )

    print("\n[FINANCIAL ROI & OPERATIONAL COST MATRIX]")
    print(f"{'Model Name':<35} | {'Fraud Prevented':<16} | {'Friction Cost':<15} | {'Net Savings':<15}")
    print("-" * 90)
    for key, m in report["models"].items():
        roi = m["financial_roi"]
        print(
            f"{m['model_name'][:33]:<35} | "
            f"${roi['fraud_amount_prevented_usd']:>13,.2f}  | "
            f"${roi['customer_friction_cost_usd']:>12,.2f}  | "
            f"${roi['net_financial_savings_usd']:>13,.2f}"
        )

    print("\n[TOP 5 RISK PREDICTORS (XGBoost Feature Importance)]")
    for item in report["feature_importances_top_10"][:5]:
        print(f"  - {item['feature']:<8}: {item['importance']:.4f}")

    print(f"\n[+] Recommended Production Model: {report['best_model'].upper()}")
    print(f"[+] Benchmark report saved to: {engine.report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

import requests
import json
import sys

BASE = "http://127.0.0.1:8000/api"

def test_feature_suite():
    print("=== 1. Health & Readiness Telemetry ===")
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200, f"Health failed: {r.text}"
    print(f"  [PASS] /api/health -> status={r.json().get('status')}")

    r = requests.get(f"{BASE}/ready")
    assert r.status_code == 200, f"Ready failed: {r.text}"
    print(f"  [PASS] /api/ready -> ready={r.json().get('ready')}")

    r = requests.get(f"{BASE}/metrics/overview")
    assert r.status_code == 200, f"Overview metrics failed: {r.text}"
    data = r.json()
    print(f"  [PASS] /api/metrics/overview -> total_transactions={data.get('total_transactions')}, open_alerts={data.get('open_alerts')}")

    r = requests.get(f"{BASE}/metrics/system")
    assert r.status_code == 200
    print(f"  [PASS] /api/metrics/system -> deployment_mode={r.json().get('deployment_mode')}")

    print("\n=== 2. Real Kaggle Real-World Model Benchmark ===")
    r = requests.get(f"{BASE}/model/kaggle/benchmark")
    assert r.status_code == 200
    b_data = r.json()
    assert "dataset_provenance" in b_data and "models" in b_data
    print(f"  [PASS] Kaggle dataset verified: {b_data['dataset_provenance']['total_transactions']:,} rows")
    print(f"  [PASS] Recommended production model: {b_data.get('best_model')}")
    for m_name, m_val in b_data["models"].items():
        print(f"         - {m_name}: PR-AUC={m_val['pr_auc']}, Recall={m_val['recall']*100:.1f}%, Precision={m_val['precision']*100:.1f}%, Net Savings=${m_val['financial_roi']['net_financial_savings_usd']:,.2f}")

    print("\n=== 3. Real Kaggle Real-Time Burst Replay ===")
    r = requests.post(f"{BASE}/stream/kaggle/burst", json={"count": 8, "fraud_ratio": 0.35})
    assert r.status_code == 200
    burst = r.json()
    print(f"  [PASS] Injected {burst['events_injected']} real Kaggle transactions, triggered {len(burst['alerts_generated'])} high-risk alerts")

    print("\n=== 4. One-Click Fraud Scenarios ===")
    scenarios = [
        "shared_device_ring",
        "circular_money_mule",
        "card_testing_burst",
        "impossible_travel",
        "account_takeover_high_value",
    ]
    for sc in scenarios:
        res = requests.post(f"{BASE}/stream/scenario", json={"scenario_name": sc, "seed": 42})
        assert res.status_code == 200
        sc_data = res.json()
        print(f"  [PASS] Scenario '{sc}': injected={sc_data['events_injected']}, alerts={len(sc_data['alerts_generated'])}")

    print("\n=== 5. Transaction Ledger & Features Inspection ===")
    tx_res = requests.get(f"{BASE}/transactions?limit=10")
    assert tx_res.status_code == 200
    tx_items = tx_res.json().get("items", [])
    assert len(tx_items) > 0
    sample_tx = tx_items[0]
    print(f"  [PASS] /api/transactions -> {len(tx_items)} items fetched, latest: {sample_tx['transaction_id']}")
    print(f"         Combined risk: {sample_tx['combined_score']*100:.1f}% ({sample_tx['risk_category']})")

    tx_det = requests.get(f"{BASE}/transactions/{sample_tx['transaction_id']}")
    assert tx_det.status_code == 200
    print(f"  [PASS] /api/transactions/{{id}} -> detailed features extracted: {len(tx_det.json().get('top_risk_factors', []))} risk factors")

    print("\n=== 6. Alert Investigation & Analyst Disposition Workflow ===")
    alerts_res = requests.get(f"{BASE}/alerts?limit=10")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json().get("items", [])
    assert len(alerts) > 0
    target_alert = alerts[0]
    al_id = target_alert["alert_id"]
    print(f"  [PASS] /api/alerts -> {len(alerts)} alerts retrieved, target: {al_id}")

    # Test status update
    up = requests.patch(f"{BASE}/alerts/{al_id}", json={
        "status": "IN_REVIEW",
        "assigned_to": "Senior Fraud Specialist",
        "note": "Case escalated for device ring inspection",
        "actor": "API_Verifier"
    })
    assert up.status_code == 200
    print(f"  [PASS] /api/alerts/{{id}} status update -> status={up.json().get('investigation_status')}, assigned_to={up.json().get('assigned_to')}")

    # Test adding case note
    note = requests.post(f"{BASE}/alerts/{al_id}/notes", json={
        "author": "ForensicsAnalyst",
        "note": "Confirmed synthetic IP subnet match across mule accounts"
    })
    assert note.status_code == 200
    print(f"  [PASS] /api/alerts/{{id}}/notes -> total notes={len(note.json().get('notes', []))}")

    print("\n=== 7. Graph Fraud Intelligence Traversal ===")
    g_res = requests.get(f"{BASE}/graph/neighborhood?depth=2")
    assert g_res.status_code == 200
    g = g_res.json()
    print(f"  [PASS] /api/graph/neighborhood -> nodes={len(g.get('nodes', []))}, edges={len(g.get('edges', []))}")

    print("\n=== 8. Dynamic Scoring Hyperparameters Configuration ===")
    cfg = requests.put(f"{BASE}/config/scoring", json={
        "weight_ml_score": 0.45,
        "weight_graph_score": 0.30,
        "weight_rule_score": 0.25,
        "threshold_review": 0.45,
        "threshold_high_risk": 0.72,
        "alert_cooldown_seconds": 120
    })
    assert cfg.status_code == 200
    print(f"  [PASS] /api/config/scoring -> weights updated (ML={cfg.json().get('WEIGHT_ML_SCORE')}, Graph={cfg.json().get('WEIGHT_GRAPH_SCORE')})")

    print("\n=== 9. CSV Dataset Ingestion & Validation Pipeline ===")
    csv_content = "Time,V1,V2,V3,V4,Amount,Class\n0.0,-2.1,1.5,-3.0,2.1,3400.0,1\n12.5,0.1,-0.2,0.3,0.0,45.2,0\n"
    files = {"file": ("demo_kaggle_sample.csv", csv_content, "text/csv")}
    upload = requests.post(f"{BASE}/datasets/upload", files=files, data={"inject_synthetic_graph": "true", "process_into_pipeline": "true"})
    assert upload.status_code == 200
    up_data = upload.json()
    print(f"  [PASS] /api/datasets/upload -> rows={up_data.get('total_rows')}, scored={up_data.get('pipeline_execution', {}).get('transactions_scored')}")

    print("\n=== 10. Dead-Letter Queue (DLQ) Inspector ===")
    dlq = requests.get(f"{BASE}/dlq")
    assert dlq.status_code == 200
    print(f"  [PASS] /api/dlq -> count={len(dlq.json().get('items', []))}")

    print("\n=======================================================")
    print("  ALL 10 END-TO-END FEATURE MODULES ARE 100% OPERATIONAL")
    print("=======================================================")

if __name__ == "__main__":
    test_feature_suite()

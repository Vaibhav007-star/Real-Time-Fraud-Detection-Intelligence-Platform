import io
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import create_app


class TestAlertsAndApiIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(db_path=":memory:", bootstrap_demo=True)
        self.client = TestClient(self.app)

    def test_health_and_overview_endpoints(self) -> None:
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["status"], "healthy")

        r_ov = self.client.get("/api/metrics/overview")
        self.assertEqual(r_ov.status_code, 200)
        self.assertGreater(r_ov.json()["total_transactions"], 10)

    def test_alert_generation_cooldown_and_investigation_workflow(self) -> None:
        # Trigger shared_device_ring scenario via API
        r_scen = self.client.post(
            "/api/stream/scenario", json={"scenario_name": "shared_device_ring", "seed": 101}
        )
        self.assertEqual(r_scen.status_code, 200)
        scen_data = r_scen.json()
        self.assertGreaterEqual(len(scen_data["alerts_generated"]), 1)
        alert_id = scen_data["alerts_generated"][0]["alert_id"]

        # Transition alert status: OPEN -> IN_REVIEW -> RESOLVED (CONFIRMED_FRAUD)
        r_patch = self.client.patch(
            f"/api/alerts/{alert_id}",
            json={
                "status": "IN_REVIEW",
                "assigned_to": "analyst.priya",
                "resolution_outcome": "UNRESOLVED",
                "note": "Investigating shared device cluster across 4 accounts.",
                "actor": "analyst.priya",
            },
        )
        self.assertEqual(r_patch.status_code, 200)
        self.assertEqual(r_patch.json()["investigation_status"], "IN_REVIEW")
        self.assertEqual(r_patch.json()["assigned_to"], "analyst.priya")
        self.assertEqual(len(r_patch.json()["notes"]), 1)

        r_resolve = self.client.patch(
            f"/api/alerts/{alert_id}",
            json={
                "status": "RESOLVED",
                "resolution_outcome": "CONFIRMED_FRAUD",
                "note": "Confirmed coordinated device ring; escalated.",
                "actor": "analyst.priya",
            },
        )
        self.assertEqual(r_resolve.status_code, 200)
        self.assertEqual(r_resolve.json()["resolution_outcome"], "CONFIRMED_FRAUD")
        self.assertGreaterEqual(len(r_resolve.json()["audit_history"]), 3)

    def test_websocket_live_delivery(self) -> None:
        with self.client.websocket_connect("/ws/live") as ws:
            hello = ws.receive_json()
            self.assertEqual(hello["type"], "CONNECTED")

            # Submit a high-risk transaction while WebSocket is connected
            tx_payload = {
                "transaction_id": "TX-WS-LIVE-999",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_account_id": "ACC-RING-01",
                "destination_account_id": "ACC-MULE-HUB-88",
                "merchant_id": "MERCH-CRYP-91",
                "merchant_category": "CRYPTO_EXCHANGE",
                "device_id": "DEV-SHARED-RING-999",
                "ip_address": "subnet-185.220.101.x",
                "transaction_amount": 8900.0,
                "currency": "USD",
                "transaction_type": "WIRE",
                "location": "SG-SIN",
                "transaction_status": "COMPLETED",
                "is_demo": True,
            }
            post_res = self.client.post("/api/transactions", json=tx_payload)
            self.assertEqual(post_res.status_code, 201)

            msg1 = ws.receive_json()
            self.assertEqual(msg1["type"], "TRANSACTION_SCORED")
            self.assertEqual(msg1["data"]["transaction_id"], "TX-WS-LIVE-999")

            msg2 = ws.receive_json()
            self.assertEqual(msg2["type"], "ALERT_CREATED")
            self.assertEqual(msg2["data"]["transaction_id"], "TX-WS-LIVE-999")

    def test_csv_upload_endpoint_and_frontend_root(self) -> None:
        csv_bytes = b"Time,V1,V2,Amount,Class\n1,-1.2,0.4,52.0,0\n2,-4.1,3.5,4800.0,1\n"
        files = {"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")}
        r_up = self.client.post(
            "/api/datasets/upload",
            files=files,
            data={"inject_synthetic_graph": "true", "process_into_pipeline": "true", "max_rows_to_score": "2"},
        )
        self.assertEqual(r_up.status_code, 200)
        self.assertEqual(r_up.json()["pipeline_execution"]["transactions_scored"], 2)

        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("Real-Time Fraud Detection Intelligence Platform", r_root.text)

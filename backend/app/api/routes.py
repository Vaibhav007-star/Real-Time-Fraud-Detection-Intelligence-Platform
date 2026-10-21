import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile

from app.core.config import settings
from app.ingestion.csv_loader import CSVDatasetInspector
from app.schemas.alert import AlertNoteCreate, AlertStatusUpdate
from app.schemas.system import (
    ScenarioTriggerRequest,
    ScoringConfigUpdateRequest,
    StreamControlRequest,
)


def create_api_router(orchestrator: Any) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, Any]:
        db_health = orchestrator.db.check_health()
        return {
            "status": "healthy" if db_health.get("status") == "healthy" else "degraded",
            "service": settings.app_name,
            "environment": settings.app_env,
            "database": db_health,
            "model_loaded": orchestrator.ml_pipeline.model_loaded,
            "model_version": orchestrator.ml_pipeline.model_version,
            "stream": orchestrator.stream_status(),
        }

    @router.get("/ready", tags=["Health"])
    async def readiness_check() -> Dict[str, Any]:
        db_health = orchestrator.db.check_health()
        if db_health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Database is not ready")
        return {"ready": True, "model_version": orchestrator.ml_pipeline.model_version}

    @router.get("/metrics/overview", tags=["Metrics"])
    async def get_overview_metrics() -> Dict[str, Any]:
        agg = orchestrator.db.get_overview_aggregates()
        op = orchestrator.metrics.snapshot()
        return {
            **agg,
            "current_tps": op["current_tps"],
            "avg_scoring_latency_ms": op["avg_scoring_latency_ms"],
            "p95_scoring_latency_ms": op["p95_scoring_latency_ms"],
            "stream_status": orchestrator.stream_status(),
            "model_health": {
                "loaded": orchestrator.ml_pipeline.model_loaded,
                "model_version": orchestrator.ml_pipeline.model_version,
                "trained_at": orchestrator.ml_pipeline.trained_at,
            },
        }

    @router.get("/metrics/system", tags=["Metrics"])
    async def get_system_health_metrics() -> Dict[str, Any]:
        db_health = orchestrator.db.check_health()
        op = orchestrator.metrics.snapshot()
        agg = orchestrator.db.get_overview_aggregates()
        return {
            "deployment_mode": "LOCAL_DEMO_STREAMING" if not orchestrator.kafka.connected else "KAFKA_CLUSTER_STREAMING",
            "kafka": orchestrator.kafka.health_status(),
            "active_ingestion_mode": "kafka" if orchestrator.kafka.connected else "in_process",
            "stream_running": orchestrator.stream_running,
            "stream_paused": orchestrator.stream_paused,
            "processing_throughput_tps": op["current_tps"],
            "avg_scoring_latency_ms": op["avg_scoring_latency_ms"],
            "p95_scoring_latency_ms": op["p95_scoring_latency_ms"],
            "failed_event_count": agg["failed_event_count"],
            "duplicate_events_handled": op["duplicate_events_handled"],
            "late_events_handled": op["late_events_handled"],
            "suppressed_duplicate_alerts": orchestrator.alert_manager.suppressed_count,
            "websocket": orchestrator.ws_manager.health_info(),
            "model": {
                "available": orchestrator.ml_pipeline.model_loaded,
                "version": orchestrator.ml_pipeline.model_version,
                "trained_at": orchestrator.ml_pipeline.trained_at,
                "scoring_mode": "supervised_nonlinear_ensemble"
                if orchestrator.ml_pipeline.model_loaded
                else "unsupervised_anomaly_fallback",
            },
            "database": db_health,
            "graph": {
                "active_nodes": len(orchestrator.graph_engine.nodes),
                "max_nodes": orchestrator.graph_engine.max_nodes,
                "lookback_seconds": orchestrator.graph_engine.lookback_seconds,
            },
            "recent_errors": op["recent_errors"],
            "uptime_seconds": op["uptime_seconds"],
        }

    @router.post("/transactions", status_code=201, tags=["Transactions"])
    async def submit_transaction(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        result = await orchestrator.process_transaction_async(payload)
        if result["status"] == "REJECTED":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": result["error"],
                    "dlq_id": result["dlq_id"],
                    "ingestion_timestamp": result["ingestion_timestamp"],
                },
            )
        return result

    @router.get("/transactions", tags=["Transactions"])
    async def list_transactions(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        risk_category: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
        sort_by: str = Query("event_timestamp"),
        sort_order: str = Query("desc"),
    ) -> Dict[str, Any]:
        items, total = orchestrator.db.list_transactions(
            limit=limit,
            offset=offset,
            risk_category=risk_category,
            search=search,
            min_score=min_score,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @router.get("/transactions/{transaction_id}", tags=["Transactions"])
    async def get_transaction_detail(transaction_id: str) -> Dict[str, Any]:
        tx = orchestrator.db.get_transaction(transaction_id)
        if not tx:
            raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found")
        return tx

    @router.get("/dlq", tags=["Transactions"])
    async def list_dead_letter_queue(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
        items = orchestrator.db.list_dead_letters(limit=limit)
        return {"items": items, "count": len(items)}

    @router.get("/alerts", tags=["Alerts"])
    async def list_alerts(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        severity: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        resolved_only: Optional[bool] = Query(None),
    ) -> Dict[str, Any]:
        items, total = orchestrator.db.list_alerts(
            limit=limit,
            offset=offset,
            severity=severity,
            status=status,
            search=search,
            resolved_only=resolved_only,
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @router.get("/alerts/{alert_id}", tags=["Alerts"])
    async def get_alert_detail(alert_id: str) -> Dict[str, Any]:
        alert = orchestrator.db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
        tx = orchestrator.db.get_transaction(alert["transaction_id"])
        subgraph = orchestrator.graph_engine.get_entity_neighborhood(
            center_id=alert["account_id"], max_depth=2
        )
        return {"alert": alert, "transaction": tx, "subgraph": subgraph}

    @router.patch("/alerts/{alert_id}", tags=["Alerts"])
    async def update_alert_status(alert_id: str, update: AlertStatusUpdate) -> Dict[str, Any]:
        updated = orchestrator.db.update_alert_investigation(
            alert_id=alert_id,
            status=update.status,
            assigned_to=update.assigned_to,
            resolution_outcome=update.resolution_outcome,
            note=update.note,
            actor=update.actor,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
        await orchestrator.ws_manager.broadcast("ALERT_UPDATED", updated)
        return updated

    @router.post("/alerts/{alert_id}/notes", tags=["Alerts"])
    async def add_alert_investigation_note(alert_id: str, payload: AlertNoteCreate) -> Dict[str, Any]:
        updated = orchestrator.db.add_alert_note(
            alert_id=alert_id, author=payload.author, note=payload.note
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
        await orchestrator.ws_manager.broadcast("ALERT_UPDATED", updated)
        return updated

    @router.get("/graph/neighborhood", tags=["Graph Intelligence"])
    async def explore_graph_neighborhood(
        entity_id: Optional[str] = Query(None, description="Account, Device, IP, or Merchant ID"),
        depth: int = Query(2, ge=1, le=3),
        node_types: Optional[str] = Query(None, description="Comma-separated node types: ACCOUNT,DEVICE,IP,MERCHANT,TRANSACTION"),
    ) -> Dict[str, Any]:
        parsed_types = [t.strip() for t in node_types.split(",") if t.strip()] if node_types else None
        return orchestrator.graph_engine.get_entity_neighborhood(
            center_id=entity_id, max_depth=depth, node_types=parsed_types
        )

    @router.get("/model/evaluation", tags=["Machine Learning"])
    async def get_model_evaluation() -> Dict[str, Any]:
        if not orchestrator.ml_pipeline.evaluation_report_:
            return {
                "available": False,
                "model_version": orchestrator.ml_pipeline.model_version,
                "reason": "No evaluation report available.",
            }
        # Also compute live stream evaluation if labeled transactions exist in DB
        txs, _ = orchestrator.db.list_transactions(limit=500)
        labeled = [t for t in txs if t.get("fraud_label") in (0, 1)]
        live_eval: Dict[str, Any] = {"available": False, "reason": "Insufficient labeled live transactions"}
        if len(labeled) >= 10:
            from app.ml.pipeline import compute_binary_metrics
            import numpy as np

            y_true = np.asarray([int(t["fraud_label"]) for t in labeled], dtype=int)
            y_scores = np.asarray([float(t["combined_score"]) for t in labeled], dtype=float)
            live_eval = compute_binary_metrics(
                y_true, y_scores, threshold=settings.threshold_review, k_alert_volume=min(20, len(labeled))
            )

        return {
            "available": True,
            **orchestrator.ml_pipeline.evaluation_report_,
            "live_stream_evaluation": live_eval,
        }

    @router.post("/model/retrain", tags=["Machine Learning"])
    async def retrain_model(seed: int = Body(42, embed=True)) -> Dict[str, Any]:
        report = orchestrator.ml_pipeline.train_and_evaluate(seed=seed, num_streams=650)
        orchestrator.db.save_model_metadata(
            orchestrator.ml_pipeline.model_version,
            report["model_type"],
            report["trained_at"],
            orchestrator.ml_pipeline.feature_names,
            report,
        )
        return report

    @router.get("/model/kaggle/benchmark", tags=["Machine Learning"])
    async def get_kaggle_benchmark() -> Dict[str, Any]:
        """Returns the out-of-time benchmark results on the official real-world Kaggle creditcard dataset
        comparing Logistic Regression, Random Forest, and XGBoost with ROI matrices.
        """
        try:
            return orchestrator.kaggle_benchmark.get_or_run_benchmark()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Kaggle benchmark evaluation failed: {exc}")

    @router.post("/stream/kaggle/burst", tags=["Streaming & Demo"])
    async def trigger_kaggle_replay_burst(
        count: int = Body(15, embed=True),
        fraud_ratio: float = Body(0.35, embed=True),
    ) -> Dict[str, Any]:
        """Replays genuine transactions from the real Kaggle credit card fraud dataset
        into the real-time scoring, graph intelligence, and alert generation pipeline.
        """
        try:
            events = orchestrator.kaggle_benchmark.get_real_sample_transactions(
                count=min(max(1, count), 100), fraud_ratio=fraud_ratio
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to sample Kaggle transactions: {exc}")

        processed_txs = []
        created_alerts = []
        for raw_ev in events:
            res = await orchestrator.process_transaction_async(raw_ev, bypass_cooldown=True)
            if res.get("transaction"):
                processed_txs.append(res["transaction"])
            if res.get("alert"):
                created_alerts.append(res["alert"])

        return {
            "source": "kaggle_real_world_creditcard_dataset",
            "events_injected": len(events),
            "transactions_scored": processed_txs,
            "alerts_generated": created_alerts,
        }

    @router.post("/stream/start", tags=["Streaming & Demo"])
    async def start_stream(req: StreamControlRequest) -> Dict[str, Any]:
        return await orchestrator.start_stream(tps=req.tps, fraud_rate=req.fraud_rate, seed=req.seed)

    @router.post("/stream/stop", tags=["Streaming & Demo"])
    async def stop_stream() -> Dict[str, Any]:
        return await orchestrator.stop_stream()

    @router.post("/stream/pause", tags=["Streaming & Demo"])
    async def pause_stream(pause: bool = Body(True, embed=True)) -> Dict[str, Any]:
        return orchestrator.pause_or_resume_stream(pause=pause)

    @router.get("/stream/status", tags=["Streaming & Demo"])
    async def stream_status() -> Dict[str, Any]:
        return orchestrator.stream_status()

    @router.post("/stream/scenario", tags=["Streaming & Demo"])
    async def trigger_demo_scenario(req: ScenarioTriggerRequest) -> Dict[str, Any]:
        events = orchestrator.generator.generate_scenario(req.scenario_name)
        processed_txs = []
        created_alerts = []
        for raw_ev in events:
            res = await orchestrator.process_transaction_async(raw_ev, bypass_cooldown=True)
            if res.get("transaction"):
                processed_txs.append(res["transaction"])
            if res.get("alert"):
                created_alerts.append(res["alert"])
        return {
            "scenario_name": req.scenario_name,
            "is_demo": True,
            "events_injected": len(events),
            "transactions_scored": processed_txs,
            "alerts_generated": created_alerts,
        }

    @router.post("/datasets/upload", tags=["Datasets"])
    async def upload_and_validate_csv(
        file: UploadFile = File(...),
        inject_synthetic_graph: bool = Form(True),
        process_into_pipeline: bool = Form(True),
        max_rows_to_score: int = Form(40),
        column_mapping_json: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only .csv files are supported.")
        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"CSV file exceeds maximum size limit ({settings.max_upload_bytes} bytes).",
            )
        col_map = None
        if column_mapping_json:
            try:
                col_map = json.loads(column_mapping_json)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Invalid column_mapping_json: {exc}")

        try:
            summary, records = CSVDatasetInspector.analyze_and_convert(
                csv_bytes=content,
                filename=file.filename,
                column_mapping=col_map,
                inject_synthetic_graph=inject_synthetic_graph,
                max_rows=min(max_rows_to_score, 500),
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Dataset validation failed: {exc}")

        scored_count = 0
        alerts_triggered = 0
        if process_into_pipeline:
            for rec in records[:max_rows_to_score]:
                res = await orchestrator.process_transaction_async(rec)
                if res.get("status") == "PROCESSED":
                    scored_count += 1
                if res.get("alert"):
                    alerts_triggered += 1

        summary["pipeline_execution"] = {
            "processed_into_pipeline": process_into_pipeline,
            "transactions_scored": scored_count,
            "alerts_generated": alerts_triggered,
        }
        return summary

    @router.get("/config", tags=["Configuration"])
    async def get_configuration() -> Dict[str, Any]:
        return settings.to_public_dict()

    @router.put("/config/scoring", tags=["Configuration"])
    async def update_scoring_configuration(req: ScoringConfigUpdateRequest) -> Dict[str, Any]:
        try:
            return settings.update_scoring_config(
                weight_ml=req.weight_ml_score,
                weight_graph=req.weight_graph_score,
                weight_rule=req.weight_rule_score,
                threshold_review=req.threshold_review,
                threshold_high_risk=req.threshold_high_risk,
                alert_cooldown_seconds=req.alert_cooldown_seconds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return router

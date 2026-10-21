from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import create_api_router
from app.core.config import BASE_PROJECT_DIR, settings
from app.core.logging import get_logger
from app.services.orchestrator import FraudPlatformOrchestrator

logger = get_logger("app.main")


from contextlib import asynccontextmanager


def create_app(db_path: str = None, bootstrap_demo: bool = True) -> FastAPI:
    orchestrator = FraudPlatformOrchestrator(db_path=db_path)
    if bootstrap_demo:
        orchestrator.bootstrap_demo_seed_data(count=28)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await orchestrator.stop_stream()

    app = FastAPI(
        title=settings.app_name,
        version="1.2.0",
        description=(
            "Enterprise Real-Time Fraud Detection Intelligence Platform combining streaming velocity features, "
            "supervised machine learning, explainable graph analytics, rule-based risk scoring, and live WebSocket alerts."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.orchestrator = orchestrator
    app.include_router(create_api_router(orchestrator))

    @app.websocket("/ws/live")
    async def websocket_live_endpoint(websocket: WebSocket) -> None:
        await orchestrator.ws_manager.connect(websocket)
        try:
            await websocket.send_json(
                {
                    "type": "CONNECTED",
                    "data": {
                        "message": "Connected to Real-Time Fraud Detection Intelligence Platform stream",
                        "stream_status": orchestrator.stream_status(),
                    },
                }
            )
            while True:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json({"type": "PONG", "data": {}})
        except WebSocketDisconnect:
            orchestrator.ws_manager.disconnect(websocket)
        except Exception:
            orchestrator.ws_manager.disconnect(websocket)

    # Serve pre-built frontend dashboard if present
    frontend_dist = BASE_PROJECT_DIR / "frontend" / "dist"
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard_root():
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(
            {
                "service": settings.app_name,
                "status": "running",
                "docs_url": "/docs",
                "api_health": "/api/health",
            }
        )

    return app


app = create_app()

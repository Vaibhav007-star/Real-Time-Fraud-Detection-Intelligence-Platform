import asyncio
import json
from typing import Any, Dict, List, Set
from fastapi import WebSocket


class WebSocketConnectionManager:
    """Manages active WebSocket client connections for real-time transaction and fraud alert push updates."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not self.active_connections:
            return
        message = json.dumps({"type": event_type, "data": payload}, default=str)
        stale: List[WebSocket] = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

    def health_info(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "connected_clients": len(self.active_connections),
        }

"""WebSocket manager for live location broadcasts."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._trip_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, trip_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._trip_connections.setdefault(trip_id, set()).add(websocket)

    def disconnect(self, trip_id: str, websocket: WebSocket) -> None:
        conns = self._trip_connections.get(trip_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._trip_connections[trip_id]

    async def broadcast(self, trip_id: str, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in self._trip_connections.get(trip_id, set()):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(trip_id, ws)

    async def send_personal(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        await websocket.send_json(payload)


ws_manager = ConnectionManager()

"""WebSocket connection registry for live monitoring updates."""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track connected monitoring clients and broadcast structured events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        await websocket.send_json(
            {
                "event": "connection.ready",
                "message": "Connected to NetPulse monitoring updates.",
            }
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for connection in list(self._connections):
            try:
                await connection.send_json(payload)
            except Exception:
                logger.debug("Dropping stale WebSocket connection", exc_info=True)
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()

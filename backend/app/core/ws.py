"""In-process WebSocket broadcast for live job status updates.

Works correctly for a single backend process, which is today's actual
deployment (one uvicorn process, no horizontal scaling). A multi-replica
deployment would need Redis pub/sub instead — fan out a status change to
Redis, have every replica's WebSocket handler subscribe and forward to its
own connected clients — which is the design docs/ARCHITECTURE.md originally
sketched for Redis. Not built because nothing in this project runs more than
one backend process; revisit if that changes.
"""

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast_json(self, message: dict) -> None:
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_json_threadsafe(self, message: dict) -> None:
        """Call from a sync endpoint (FastAPI runs `def` handlers in a worker
        thread) to schedule a broadcast onto the event loop that's actually
        running the WebSocket connections."""
        if self.loop is None:
            logger.warning("broadcast attempted before event loop was captured; dropping message")
            return
        asyncio.run_coroutine_threadsafe(self.broadcast_json(message), self.loop)


manager = ConnectionManager()

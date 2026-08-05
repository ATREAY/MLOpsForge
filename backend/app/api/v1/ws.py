"""WebSocket endpoint for live job status. Not wired through the normal
get_current_user dependency — browsers can't attach an Authorization header
to a WebSocket handshake, so the token travels as a query param instead and
is validated by hand here."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_access_token
from app.core.ws import manager
from app.db.session import SessionLocal
from app.models.user import User

router = APIRouter()


def _authenticate(token: str | None) -> User | None:
    if not token:
        return None
    try:
        user_id = decode_access_token(token)
    except JWTError:
        return None

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
    finally:
        db.close()
    return user if (user is not None and user.is_active) else None


@router.websocket("/ws/jobs")
async def jobs_ws(websocket: WebSocket):
    user = _authenticate(websocket.query_params.get("token"))
    if user is None:
        await websocket.close(code=1008)  # policy violation
        return

    await manager.connect(websocket)
    try:
        while True:
            # This endpoint is broadcast-only; the loop just keeps the
            # connection alive and detects disconnects. Any inbound message
            # (e.g. a ping) is read and discarded.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

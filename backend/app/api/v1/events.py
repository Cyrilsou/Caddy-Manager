import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.models.user import User
from app.security.rbac import require_permission

router = APIRouter(prefix="/events", tags=["events"])
logger = logging.getLogger(__name__)

_subscribers: list[asyncio.Queue] = []


def broadcast_event(event_type: str, data: dict):
    """Push an event to all connected SSE clients."""
    payload = json.dumps({"type": event_type, **data}, default=str)
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


@router.get("/stream")
async def event_stream(
    request: Request,
    _: User = Depends(require_permission("domain.read")),
):
    """SSE stream for real-time dashboard updates."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(queue)

    async def generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _subscribers.remove(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

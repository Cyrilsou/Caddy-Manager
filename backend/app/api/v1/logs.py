import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.models.user import User
from app.security.rbac import require_permission

router = APIRouter(prefix="/logs", tags=["logs"])
logger = logging.getLogger(__name__)

# In-memory log buffer for SSE streaming (last 1000 lines)
_log_buffer: list[str] = []
_log_subscribers: list[asyncio.Queue] = []
MAX_BUFFER = 1000


def push_log_entry(entry: dict):
    """Called by log handlers to push entries to SSE subscribers."""
    line = json.dumps(entry, default=str)
    _log_buffer.append(line)
    if len(_log_buffer) > MAX_BUFFER:
        _log_buffer.pop(0)
    for q in _log_subscribers:
        try:
            q.put_nowait(line)
        except asyncio.QueueFull:
            pass


@router.get("/stream")
async def stream_logs(
    request: Request,
    _: User = Depends(require_permission("audit.read")),
):
    """Server-Sent Events stream of application logs."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _log_subscribers.append(queue)

    async def event_generator():
        try:
            # Send buffered history first
            for line in _log_buffer[-50:]:
                yield f"data: {line}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _log_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def recent_logs(
    limit: int = 100,
    _: User = Depends(require_permission("audit.read")),
):
    """Get recent log entries from buffer."""
    entries = []
    for line in _log_buffer[-limit:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append({"raw": line})
    return entries

"""
SSE endpoint — GET /api/events

Clients connect once and receive a continuous stream of server-sent events.
The connection is kept alive with a 'ping' event every 30 seconds.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from mountrr.events import bus

router = APIRouter(tags=["events"])
logger = logging.getLogger(__name__)

PING_INTERVAL = 30  # seconds


@router.get("/events")
async def event_stream() -> StreamingResponse:
    return StreamingResponse(
        _generate(bus.subscribe()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


async def _generate(queue: asyncio.Queue):
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                yield f"data: {message}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive ping
                ping = json.dumps(
                    {
                        "event": "ping",
                        "payload": {},
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }
                )
                yield f"data: {ping}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        bus.unsubscribe(queue)
        logger.debug("SSE stream closed")

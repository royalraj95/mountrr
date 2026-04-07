"""
SSE event bus.

A single in-process EventBus holds a set of asyncio.Queue subscribers.
GET /api/events registers a new subscriber and streams events.
The scanner and deletion logic call EventBus.publish() to broadcast events.

Event types:
    scan.started        {"scan_id": int, "scan_type": str}
    scan.progress       {"scan_id": int, "scanned": int, "broken": int}
    scan.completed      {"scan_id": int, "total": int, "broken_found": int}
    scan.error          {"scan_id": int, "error": str}
    mount.health_changed {"mount": str, "old": str, "new": str}
    symlink.deleted     {"symlink_path": str, "dry_run": bool}
    ping                {}  — keepalive, sent every 30s
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        logger.debug("SSE subscriber added (%d total)", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)
        logger.debug("SSE subscriber removed (%d remaining)", len(self._subscribers))

    async def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        if not self._subscribers:
            return
        message = json.dumps(
            {
                "event": event,
                "payload": payload or {},
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                # Slow consumer — drop and remove
                logger.warning("SSE subscriber queue full — removing slow consumer")
                dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Module-level singleton used throughout the application
bus = EventBus()

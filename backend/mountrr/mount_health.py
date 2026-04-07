"""
Mount health detection.

SAFETY RULE: Symlinks are only marked 'broken' when their mount is 'healthy'.
If a mount is 'empty' or 'unreachable', symlinks pointing there are left as
'unknown' — never marked broken. This prevents catastrophic mass-deletion
during a transient rclone/FUSE mount failure.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

MountStatus = Literal["healthy", "empty", "unreachable"]


def check_mount_health_sync(mount_path: str) -> MountStatus:
    """
    Synchronous mount health check. Use check_mount_health() in async context.

    Returns:
        'healthy'     — mount accessible, ≥1 entry visible
        'empty'       — mount accessible, os.listdir() returns []
        'unreachable' — path doesn't exist, or OSError (transport endpoint not connected)
    """
    try:
        if not os.path.exists(mount_path):
            return "unreachable"
        contents = os.listdir(mount_path)
        return "healthy" if contents else "empty"
    except OSError as exc:
        # Common: [Errno 107] Transport endpoint is not connected (FUSE unmounted)
        logger.debug("Mount %s OSError: %s", mount_path, exc)
        return "unreachable"


async def check_mount_health(mount_path: str) -> MountStatus:
    """Async wrapper — runs the blocking check in a thread pool."""
    return await asyncio.to_thread(check_mount_health_sync, mount_path)


async def check_all_mounts(rd_path: str, nzb_path: str) -> dict[str, MountStatus]:
    """Check both mounts concurrently."""
    rd_status, nzb_status = await asyncio.gather(
        check_mount_health(rd_path),
        check_mount_health(nzb_path),
    )
    return {"rd": rd_status, "nzb": nzb_status}

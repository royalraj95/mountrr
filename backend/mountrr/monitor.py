"""
Watchdog filesystem monitor — v1.1

This module is a placeholder. Real-time directory monitoring via watchdog
is scoped to v1.1. The class is defined here so imports don't break.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SymlinkMonitor:
    """
    Watches /media directories for symlink create/delete/modify events.
    Deferred to v1.1 — not started in v1.0.
    """

    def __init__(self) -> None:
        self._started = False

    def start(self) -> None:
        logger.info("SymlinkMonitor: watchdog monitoring is not yet implemented (v1.1 feature)")

    def stop(self) -> None:
        pass

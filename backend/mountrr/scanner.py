"""
Symlink scanner.

Walks configured media directories, classifies each symlink, checks mount health,
and determines ok/broken/unknown status. Results are upserted into the symlinks
table. Scan progress and results are broadcast via the SSE event bus.

SAFETY: Never marks symlinks as broken if their mount is unreachable or empty.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal

from mountrr import database as db
from mountrr.classifier import classify_symlink
from mountrr.config import coerce_setting
from mountrr.events import bus
from mountrr.mount_health import check_all_mounts

logger = logging.getLogger(__name__)

ScanType = Literal["full", "broken_only"]

# Global flag to prevent concurrent scans
_scan_running = False
_current_scan_id: int | None = None


def is_scan_running() -> bool:
    return _scan_running


def current_scan_id() -> int | None:
    return _current_scan_id


async def run_scan(scan_type: ScanType = "full") -> int:
    """
    Run a scan. Returns the scan_history.id.
    Raises RuntimeError if a scan is already running.
    """
    global _scan_running, _current_scan_id

    if _scan_running:
        raise RuntimeError("A scan is already running")

    _scan_running = True

    # Insert scan_history row
    scan_id = await db.execute(
        "INSERT INTO scan_history(scan_type) VALUES (?)", (scan_type,)
    )
    _current_scan_id = scan_id

    await bus.publish("scan.started", {"scan_id": scan_id, "scan_type": scan_type})
    logger.info("Scan #%d started (type=%s)", scan_id, scan_type)

    total = 0
    broken = 0

    try:
        # Load config from DB
        rd_patterns = coerce_setting(
            "rd_patterns", await db.get_setting("rd_patterns", '["decypharr","realdebrid","zurg","rd"]')
        )
        nzb_patterns = coerce_setting(
            "nzb_patterns", await db.get_setting("nzb_patterns", '["nzbdav","nzb","usenet"]')
        )
        media_dirs_raw = await db.get_setting("media_dirs", '["/media"]')
        media_dirs: list[str] = coerce_setting("media_dirs", media_dirs_raw)
        rd_mount = await db.get_setting("rd_mount_path", "/mnt/rd")
        nzb_mount = await db.get_setting("nzb_mount_path", "/mnt/nzb")

        # Check mount health once before scanning
        mount_health = await check_all_mounts(rd_mount or "/mnt/rd", nzb_mount or "/mnt/nzb")
        logger.info("Mount health: rd=%s nzb=%s", mount_health["rd"], mount_health["nzb"])

        # Emit mount health so dashboard can reflect it immediately
        for mount_name, status in mount_health.items():
            await bus.publish("mount.health_changed", {"mount": mount_name, "status": status})

        # Walk media directories and collect symlinks
        all_symlinks = await asyncio.to_thread(
            _collect_symlinks, media_dirs
        )

        progress_interval = max(1, len(all_symlinks) // 20)  # emit ~20 progress events

        for i, symlink_path in enumerate(all_symlinks):
            try:
                status, source, target_path, target_size = await asyncio.to_thread(
                    _evaluate_symlink,
                    symlink_path,
                    rd_patterns,
                    nzb_patterns,
                    mount_health,
                )
            except Exception as exc:
                logger.warning("Error evaluating %s: %s", symlink_path, exc)
                continue

            if scan_type == "broken_only" and status != "broken":
                # In broken_only mode skip upsert for non-broken symlinks
                if status == "ok":
                    total += 1
                    continue

            # Upsert into symlinks table
            await db.execute(
                """
                INSERT INTO symlinks(symlink_path, target_path, source, status, last_checked, target_size)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(symlink_path) DO UPDATE SET
                    target_path=excluded.target_path,
                    source=excluded.source,
                    status=excluded.status,
                    last_checked=excluded.last_checked,
                    target_size=excluded.target_size
                """,
                (symlink_path, target_path, source, status, target_size),
            )

            total += 1
            if status == "broken":
                broken += 1

            if (i + 1) % progress_interval == 0 or i == len(all_symlinks) - 1:
                await bus.publish(
                    "scan.progress",
                    {"scan_id": scan_id, "scanned": total, "broken": broken},
                )

        # Finalise scan_history row
        await db.execute(
            """
            UPDATE scan_history
            SET completed_at=CURRENT_TIMESTAMP, total_symlinks=?, broken_found=?
            WHERE id=?
            """,
            (total, broken, scan_id),
        )

        await bus.publish(
            "scan.completed",
            {"scan_id": scan_id, "total": total, "broken_found": broken},
        )
        logger.info(
            "Scan #%d completed: %d symlinks scanned, %d broken", scan_id, total, broken
        )

    except Exception as exc:
        logger.error("Scan #%d failed: %s", scan_id, exc, exc_info=True)
        await bus.publish("scan.error", {"scan_id": scan_id, "error": str(exc)})
        await db.execute(
            "UPDATE scan_history SET completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (scan_id,),
        )
    finally:
        _scan_running = False
        _current_scan_id = None

    return scan_id


def _collect_symlinks(media_dirs: list[str]) -> list[str]:
    """Walk directories and return all symlink paths. Runs in a thread."""
    result: list[str] = []
    for media_dir in media_dirs:
        if not os.path.isdir(media_dir):
            logger.warning("Media directory not found: %s", media_dir)
            continue
        for root, dirs, files in os.walk(media_dir, followlinks=False):
            for name in files + dirs:
                full = os.path.join(root, name)
                if os.path.islink(full):
                    result.append(full)
    return result


def _evaluate_symlink(
    symlink_path: str,
    rd_patterns: list[str],
    nzb_patterns: list[str],
    mount_health: dict[str, str],
) -> tuple[str, str, str, int | None]:
    """
    Evaluate a single symlink. Returns (status, source, target_path, target_size).
    Runs in a thread.
    """

    target_path = os.readlink(symlink_path)
    source = classify_symlink(target_path, rd_patterns, nzb_patterns)

    # Determine which mount governs this symlink
    if source == "rd":
        mount_status = mount_health.get("rd", "unreachable")
    elif source == "nzb":
        mount_status = mount_health.get("nzb", "unreachable")
    else:
        mount_status = "healthy"  # 'other' — evaluate normally

    if mount_status in ("unreachable", "empty"):
        # SAFETY: don't mark broken when mount is down
        return ("unknown", source, target_path, None)

    # Mount is healthy — check if the specific file exists
    target_exists = os.path.exists(target_path)

    if target_exists:
        try:
            target_size = os.path.getsize(target_path)
        except OSError:
            target_size = None
        return ("ok", source, target_path, target_size)
    else:
        return ("broken", source, target_path, None)

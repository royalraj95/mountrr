from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from mountrr import database as db
from mountrr.config import coerce_setting
from mountrr.models import (
    BySourceCount,
    DashboardResponse,
    MountHealthMap,
    RecentActivityItem,
    ScanHistoryRow,
)
from mountrr.mount_health import check_all_mounts

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard() -> DashboardResponse:
    # Counts
    total = await db.count("symlinks")
    broken = await db.count("symlinks", "status = 'broken'")

    # By source
    rows = await db.fetchall(
        "SELECT source, COUNT(*) as cnt FROM symlinks GROUP BY source"
    )
    by_source = BySourceCount()
    for row in rows:
        src = row[0]
        cnt = row[1]
        if src == "rd":
            by_source.rd = cnt
        elif src == "nzb":
            by_source.nzb = cnt
        else:
            by_source.other = cnt

    # Mount health
    rd_mount = await db.get_setting("rd_mount_path", "/mnt/rd")
    nzb_mount = await db.get_setting("nzb_mount_path", "/mnt/nzb")
    health = await check_all_mounts(rd_mount or "/mnt/rd", nzb_mount or "/mnt/nzb")
    mount_health = MountHealthMap(rd=health["rd"], nzb=health["nzb"])

    # Last scan
    last_scan_row = await db.fetchone(
        "SELECT * FROM scan_history ORDER BY started_at DESC LIMIT 1"
    )
    last_scan: ScanHistoryRow | None = None
    if last_scan_row:
        last_scan = ScanHistoryRow(
            id=last_scan_row["id"],
            started_at=last_scan_row["started_at"],
            completed_at=last_scan_row["completed_at"],
            total_symlinks=last_scan_row["total_symlinks"],
            broken_found=last_scan_row["broken_found"],
            cleaned=last_scan_row["cleaned"] or 0,
            scan_type=last_scan_row["scan_type"],
        )

    # Recent activity (last 20 deletions as proxy for activity)
    activity_rows = await db.fetchall(
        "SELECT symlink_path, deleted_at FROM deletion_history ORDER BY deleted_at DESC LIMIT 20"
    )
    recent_activity = [
        RecentActivityItem(
            event="symlink.deleted",
            symlink_path=r["symlink_path"],
            timestamp=r["deleted_at"],
        )
        for r in activity_rows
    ]

    return DashboardResponse(
        total_symlinks=total,
        broken_symlinks=broken,
        by_source=by_source,
        mount_health=mount_health,
        last_scan=last_scan,
        recent_activity=recent_activity,
    )

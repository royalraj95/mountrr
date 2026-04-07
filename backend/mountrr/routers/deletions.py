from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from mountrr import database as db
from mountrr.models import (
    CleanupRequest,
    CleanupResponse,
    DeletionListResponse,
    DeletionRow,
)
from mountrr.routers.symlinks import _delete_single

router = APIRouter(tags=["deletions"])
logger = logging.getLogger(__name__)


@router.get("/deletions", response_model=DeletionListResponse)
async def list_deletions(
    cursor: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source: str = Query("all"),
    search: str = Query(""),
) -> DeletionListResponse:
    wheres: list[str] = []
    params: list = []

    if cursor:
        wheres.append("id > ?")
        params.append(cursor)
    if source != "all":
        wheres.append("source = ?")
        params.append(source)
    if search:
        wheres.append("symlink_path LIKE ?")
        params.append(f"%{search}%")

    where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""

    count_wheres = [w for w in wheres if "id >" not in w]
    count_params = [p for w, p in zip(wheres, params) if "id >" not in w]
    count_where = ("WHERE " + " AND ".join(count_wheres)) if count_wheres else ""
    total = await db.count(
        "deletion_history", count_where.replace("WHERE ", ""), tuple(count_params)
    )

    rows = await db.fetchall(
        f"SELECT * FROM deletion_history {where_clause} ORDER BY deleted_at DESC LIMIT ?",
        tuple(params) + (limit + 1,),
    )

    has_more = len(rows) > limit
    items_raw = rows[:limit]

    items = [
        DeletionRow(
            id=r["id"],
            symlink_path=r["symlink_path"],
            target_path=r["target_path"],
            source=r["source"],
            deleted_at=r["deleted_at"],
            reason=r["reason"],
            arr_search_triggered=bool(r["arr_search_triggered"]),
            arr_instance=r["arr_instance"],
            arr_search_result=r["arr_search_result"],
        )
        for r in items_raw
    ]

    next_cursor = items[-1].id if has_more and items else None
    return DeletionListResponse(items=items, next_cursor=next_cursor, total=total)


@router.post("/deletions/cleanup", response_model=CleanupResponse)
async def cleanup_broken(body: CleanupRequest = CleanupRequest()) -> CleanupResponse:
    """Delete all broken symlinks (or a specified subset)."""

    if body.symlink_ids is not None:
        rows = await db.fetchall(
            f"SELECT * FROM symlinks WHERE id IN ({','.join('?' * len(body.symlink_ids))}) AND status = 'broken'",
            tuple(body.symlink_ids),
        )
    else:
        rows = await db.fetchall("SELECT * FROM symlinks WHERE status = 'broken'")

    total_deleted = 0
    total_skipped = 0

    for row in rows:
        d, s = await _delete_single(
            symlink_id=row["id"],
            symlink_path=row["symlink_path"],
            target_path=row["target_path"],
            source=row["source"],
            reason="broken_cleanup",
            dry_run=body.dry_run,
        )
        total_deleted += d
        total_skipped += s

    logger.info(
        "Cleanup complete: deleted=%d skipped=%d dry_run=%s",
        total_deleted,
        total_skipped,
        body.dry_run,
    )
    return CleanupResponse(deleted=total_deleted, skipped=total_skipped, dry_run=body.dry_run)

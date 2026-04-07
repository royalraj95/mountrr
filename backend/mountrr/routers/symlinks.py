from __future__ import annotations

import os
import logging

from fastapi import APIRouter, HTTPException, Query

from mountrr import database as db
from mountrr.events import bus
from mountrr.models import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    SymlinkListResponse,
    SymlinkRow,
)

router = APIRouter(tags=["symlinks"])
logger = logging.getLogger(__name__)


@router.get("/symlinks", response_model=SymlinkListResponse)
async def list_symlinks(
    status: str = Query("all", pattern="^(all|ok|broken|unknown)$"),
    source: str = Query("all", pattern="^(all|rd|nzb|other)$"),
    search: str = Query(""),
    cursor: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> SymlinkListResponse:
    wheres: list[str] = []
    params: list = []

    if cursor:
        wheres.append("id > ?")
        params.append(cursor)
    if status != "all":
        wheres.append("status = ?")
        params.append(status)
    if source != "all":
        wheres.append("source = ?")
        params.append(source)
    if search:
        wheres.append("symlink_path LIKE ?")
        params.append(f"%{search}%")

    where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""

    # Count (without cursor for total)
    count_wheres = [w for w in wheres if "id >" not in w]
    count_params = [p for w, p in zip(wheres, params) if "id >" not in w]
    count_where = ("WHERE " + " AND ".join(count_wheres)) if count_wheres else ""
    total = await db.count("symlinks", count_where.replace("WHERE ", ""), tuple(count_params))

    rows = await db.fetchall(
        f"SELECT * FROM symlinks {where_clause} ORDER BY id LIMIT ?",
        tuple(params) + (limit + 1,),
    )

    has_more = len(rows) > limit
    items_raw = rows[:limit]

    items = [
        SymlinkRow(
            id=r["id"],
            symlink_path=r["symlink_path"],
            target_path=r["target_path"],
            source=r["source"],
            status=r["status"],
            first_seen=r["first_seen"],
            last_checked=r["last_checked"],
            target_size=r["target_size"],
        )
        for r in items_raw
    ]

    next_cursor = items[-1].id if has_more and items else None
    return SymlinkListResponse(items=items, next_cursor=next_cursor, total=total)


@router.delete("/symlinks/{symlink_id}", response_model=BulkDeleteResponse)
async def delete_symlink(symlink_id: int, dry_run: bool = Query(False)) -> BulkDeleteResponse:
    row = await db.fetchone("SELECT * FROM symlinks WHERE id = ?", (symlink_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Symlink not found")

    deleted, skipped = await _delete_single(
        symlink_id=row["id"],
        symlink_path=row["symlink_path"],
        target_path=row["target_path"],
        source=row["source"],
        reason="manual",
        dry_run=dry_run,
    )
    return BulkDeleteResponse(deleted=deleted, skipped=skipped, dry_run=dry_run)


@router.delete("/symlinks", response_model=BulkDeleteResponse)
async def bulk_delete_symlinks(body: BulkDeleteRequest) -> BulkDeleteResponse:
    total_deleted = 0
    total_skipped = 0

    for symlink_id in body.ids:
        row = await db.fetchone("SELECT * FROM symlinks WHERE id = ?", (symlink_id,))
        if not row:
            total_skipped += 1
            continue
        d, s = await _delete_single(
            symlink_id=row["id"],
            symlink_path=row["symlink_path"],
            target_path=row["target_path"],
            source=row["source"],
            reason="manual",
            dry_run=body.dry_run,
        )
        total_deleted += d
        total_skipped += s

    return BulkDeleteResponse(deleted=total_deleted, skipped=total_skipped, dry_run=body.dry_run)


async def _delete_single(
    *,
    symlink_id: int,
    symlink_path: str,
    target_path: str,
    source: str,
    reason: str,
    dry_run: bool,
) -> tuple[int, int]:
    """Delete one symlink. Returns (deleted, skipped) counts."""

    # Safety re-stat
    if not os.path.islink(symlink_path):
        logger.info("Symlink already gone: %s", symlink_path)
        await db.execute("DELETE FROM symlinks WHERE id = ?", (symlink_id,))
        return (0, 1)

    # Write audit row BEFORE unlink
    await db.execute(
        """
        INSERT INTO deletion_history(symlink_path, target_path, source, reason)
        VALUES (?, ?, ?, ?)
        """,
        (symlink_path, target_path, source, reason),
    )

    if dry_run:
        logger.info("[dry-run] Would delete symlink: %s", symlink_path)
        await bus.publish("symlink.deleted", {"symlink_path": symlink_path, "dry_run": True})
        return (1, 0)

    try:
        os.unlink(symlink_path)
        await db.execute("DELETE FROM symlinks WHERE id = ?", (symlink_id,))
        await bus.publish("symlink.deleted", {"symlink_path": symlink_path, "dry_run": False})
        logger.info("Deleted symlink: %s", symlink_path)
        return (1, 0)
    except OSError as exc:
        logger.error("Failed to unlink %s: %s", symlink_path, exc)
        await db.execute(
            "UPDATE deletion_history SET arr_search_result = ? "
            "WHERE symlink_path = ? ORDER BY id DESC LIMIT 1",
            (f"unlink_failed: {exc}", symlink_path),
        )
        return (0, 1)

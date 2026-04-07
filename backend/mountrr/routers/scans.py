from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from mountrr import database as db
from mountrr.models import (
    ScanHistoryResponse,
    ScanHistoryRow,
    ScanStartRequest,
    ScanStartResponse,
    ScanStatusResponse,
)
from mountrr.scanner import current_scan_id, is_scan_running, run_scan

router = APIRouter(tags=["scans"])
logger = logging.getLogger(__name__)


@router.post("/scans/start", response_model=ScanStartResponse)
async def start_scan(body: ScanStartRequest = ScanStartRequest()) -> ScanStartResponse:
    if is_scan_running():
        raise HTTPException(status_code=409, detail="A scan is already running")

    # Fire-and-forget: don't await — respond immediately, progress via SSE
    asyncio.create_task(run_scan(body.scan_type))

    # The scan_id is assigned inside run_scan; we return a pending response.
    # The client should subscribe to SSE /api/events to track progress.
    return ScanStartResponse(scan_id=0, status="started")


@router.get("/scans/status", response_model=ScanStatusResponse)
async def get_scan_status() -> ScanStatusResponse:
    running = is_scan_running()
    scan_id = current_scan_id()
    return ScanStatusResponse(running=running, scan_id=scan_id)


@router.get("/scans/history", response_model=ScanHistoryResponse)
async def get_scan_history(limit: int = 20) -> ScanHistoryResponse:
    rows = await db.fetchall(
        "SELECT * FROM scan_history ORDER BY started_at DESC LIMIT ?", (limit,)
    )
    items = [
        ScanHistoryRow(
            id=r["id"],
            started_at=r["started_at"],
            completed_at=r["completed_at"],
            total_symlinks=r["total_symlinks"],
            broken_found=r["broken_found"],
            cleaned=r["cleaned"] or 0,
            scan_type=r["scan_type"],
        )
        for r in rows
    ]
    return ScanHistoryResponse(items=items)

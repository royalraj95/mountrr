"""
All Pydantic v2 schemas used by API request/response bodies and DB row mappings.
Never define schemas inline in routers — always import from here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Symlinks
# ---------------------------------------------------------------------------

class SymlinkRow(BaseModel):
    id: int
    symlink_path: str
    target_path: str
    source: Literal["rd", "nzb", "other"]
    status: Literal["ok", "broken", "unknown"]
    first_seen: datetime
    last_checked: datetime | None = None
    target_size: int | None = None

    model_config = {"from_attributes": True}


class SymlinkListResponse(BaseModel):
    items: list[SymlinkRow]
    next_cursor: int | None = None
    total: int


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)
    dry_run: bool = False


class BulkDeleteResponse(BaseModel):
    deleted: int
    skipped: int
    dry_run: bool


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

class ScanStartRequest(BaseModel):
    scan_type: Literal["full", "broken_only"] = "full"


class ScanStartResponse(BaseModel):
    scan_id: int
    status: str


class ScanHistoryRow(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None = None
    total_symlinks: int | None = None
    broken_found: int | None = None
    cleaned: int = 0
    scan_type: Literal["full", "quick", "broken_only"]

    model_config = {"from_attributes": True}


class ScanHistoryResponse(BaseModel):
    items: list[ScanHistoryRow]


class ScanStatusResponse(BaseModel):
    running: bool
    scan_id: int | None = None
    progress: dict[str, int] | None = None


# ---------------------------------------------------------------------------
# Deletions
# ---------------------------------------------------------------------------

class DeletionRow(BaseModel):
    id: int
    symlink_path: str
    target_path: str
    source: str | None
    deleted_at: datetime
    reason: Literal["manual", "scan_cleanup", "broken_cleanup", "orphan_cleanup"]
    arr_search_triggered: bool = False
    arr_instance: str | None = None
    arr_search_result: str | None = None

    model_config = {"from_attributes": True}


class DeletionListResponse(BaseModel):
    items: list[DeletionRow]
    next_cursor: int | None = None
    total: int


class CleanupRequest(BaseModel):
    dry_run: bool = False
    symlink_ids: list[int] | None = None  # None = all broken


class CleanupResponse(BaseModel):
    deleted: int
    skipped: int
    dry_run: bool


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class MountHealthMap(BaseModel):
    rd: Literal["healthy", "empty", "unreachable"]
    nzb: Literal["healthy", "empty", "unreachable"]


class BySourceCount(BaseModel):
    rd: int = 0
    nzb: int = 0
    other: int = 0


class RecentActivityItem(BaseModel):
    event: str
    symlink_path: str | None = None
    timestamp: datetime


class DashboardResponse(BaseModel):
    total_symlinks: int
    broken_symlinks: int
    by_source: BySourceCount
    mount_health: MountHealthMap
    last_scan: ScanHistoryRow | None = None
    recent_activity: list[RecentActivityItem] = []


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsResponse(BaseModel):
    scan_interval_minutes: int = 720
    dry_run: bool = False
    rd_patterns: list[str] = ["decypharr", "realdebrid", "zurg", "rd"]
    nzb_patterns: list[str] = ["nzbdav", "nzb", "usenet"]
    media_dirs: list[str] = ["/media"]
    rd_mount_path: str = "/mnt/rd"
    nzb_mount_path: str = "/mnt/nzb"
    log_level: str = "INFO"


class SettingsUpdateRequest(BaseModel):
    """Partial update — only provided fields are changed."""
    scan_interval_minutes: int | None = None
    dry_run: bool | None = None
    rd_patterns: list[str] | None = None
    nzb_patterns: list[str] | None = None
    media_dirs: list[str] | None = None
    rd_mount_path: str | None = None
    nzb_mount_path: str | None = None
    log_level: str | None = None


# ---------------------------------------------------------------------------
# SSE events
# ---------------------------------------------------------------------------

class SSEEvent(BaseModel):
    event: str
    payload: dict[str, Any] = {}
    ts: datetime


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"

from __future__ import annotations

import json
import logging

from fastapi import APIRouter

from mountrr import database as db
from mountrr.config import coerce_setting
from mountrr.models import SettingsResponse, SettingsUpdateRequest

router = APIRouter(tags=["settings"])
logger = logging.getLogger(__name__)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    all_settings = await db.get_all_settings()

    def get(key: str, default: str) -> str:
        return all_settings.get(key, default)

    return SettingsResponse(
        scan_interval_minutes=int(get("scan_interval_minutes", "720")),
        dry_run=get("dry_run", "false").lower() in ("true", "1"),
        rd_patterns=json.loads(get("rd_patterns", '["decypharr","realdebrid","zurg","rd"]')),
        nzb_patterns=json.loads(get("nzb_patterns", '["nzbdav","nzb","usenet"]')),
        media_dirs=json.loads(get("media_dirs", '["/media"]')),
        rd_mount_path=get("rd_mount_path", "/mnt/rd"),
        nzb_mount_path=get("nzb_mount_path", "/mnt/nzb"),
        log_level=get("log_level", "INFO"),
    )


@router.put("/settings")
async def update_settings(body: SettingsUpdateRequest) -> dict:
    updates: dict[str, str] = {}

    if body.scan_interval_minutes is not None:
        updates["scan_interval_minutes"] = str(body.scan_interval_minutes)
    if body.dry_run is not None:
        updates["dry_run"] = str(body.dry_run).lower()
    if body.rd_patterns is not None:
        updates["rd_patterns"] = json.dumps(body.rd_patterns)
    if body.nzb_patterns is not None:
        updates["nzb_patterns"] = json.dumps(body.nzb_patterns)
    if body.media_dirs is not None:
        updates["media_dirs"] = json.dumps(body.media_dirs)
    if body.rd_mount_path is not None:
        updates["rd_mount_path"] = body.rd_mount_path
    if body.nzb_mount_path is not None:
        updates["nzb_mount_path"] = body.nzb_mount_path
    if body.log_level is not None:
        updates["log_level"] = body.log_level.upper()

    for key, value in updates.items():
        await db.set_setting(key, value)

    logger.info("Settings updated: %s", list(updates.keys()))
    return {"ok": True}

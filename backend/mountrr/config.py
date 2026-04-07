"""
Config loading: env vars are read at startup and used to seed the DB config table
on first boot. After that, the DB is the source of truth — UI changes persist
across restarts without touching env vars.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class EnvSettings(BaseSettings):
    """Reads from environment variables. Only used for DB seeding."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Container
    tz: str = "UTC"
    puid: int = 1000
    pgid: int = 1000
    log_level: str = "INFO"

    # Scan
    scan_interval: int = 720  # minutes; 0 = startup only
    dry_run: bool = False

    # Arr (v1.1 — seeded but not yet used by backend logic)
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


# Singleton loaded once at import time
env = EnvSettings()


# DB config keys and their initial values derived from env
def get_seed_config(settings: EnvSettings = env) -> dict[str, str]:
    """
    Returns the key→value pairs to INSERT OR IGNORE into the config table.
    Called once during startup after DB migrations run.
    """
    return {
        "scan_interval_minutes": str(settings.scan_interval),
        "dry_run": str(settings.dry_run).lower(),
        "log_level": settings.log_level,
        "rd_patterns": json.dumps(["decypharr", "realdebrid", "zurg", "rd"]),
        "nzb_patterns": json.dumps(["nzbdav", "nzb", "usenet"]),
        "media_dirs": json.dumps(["/media"]),
        "rd_mount_path": "/mnt/rd",
        "nzb_mount_path": "/mnt/nzb",
        # Arr (v1.1)
        "radarr_url": settings.radarr_url,
        "radarr_api_key": settings.radarr_api_key,
        "sonarr_url": settings.sonarr_url,
        "sonarr_api_key": settings.sonarr_api_key,
    }


def coerce_setting(key: str, raw: str) -> Any:
    """Coerce a raw config string to the appropriate Python type."""
    bool_keys = {"dry_run"}
    int_keys = {"scan_interval_minutes"}
    json_keys = {"rd_patterns", "nzb_patterns", "media_dirs"}

    if key in bool_keys:
        return raw.lower() in ("true", "1", "yes")
    if key in int_keys:
        return int(raw)
    if key in json_keys:
        return json.loads(raw)
    return raw

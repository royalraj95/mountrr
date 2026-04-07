"""
E2E test fixtures.

Each test gets:
  - A fresh temp filesystem (2 healthy + 1 broken + 1 other symlinks)
  - A fresh SQLite DB initialised via init_db(path)
  - Config seeded to point at the temp paths
  - A bare FastAPI app (no periodic scan task) with all routers mounted
  - An httpx.AsyncClient via ASGI transport
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Filesystem + DB setup
# ---------------------------------------------------------------------------

@pytest.fixture
async def e2e_setup(tmp_path):
    """
    Create a small fake mount tree and initialise a fresh DB.
    Yields a dict with all relevant paths.
    Tears down (closes DB) after the test.
    """
    # Directories
    # IMPORTANT: use full pattern strings ("realdebrid", "nzbdav") in path components,
    # not short "rd"/"nzb" which can accidentally match macOS temp folder prefixes
    # like /private/var/folders/rd/... and break classification tests.
    movies_dir = tmp_path / "media" / "movies"
    tv_dir = tmp_path / "media" / "tv"
    rd_target_dir = tmp_path / "storage" / "realdebrid" / "movies"
    nzb_target_dir = tmp_path / "storage" / "nzbdav" / "shows"
    other_dir = tmp_path / "other"

    for d in [movies_dir, tv_dir, rd_target_dir, nzb_target_dir, other_dir]:
        d.mkdir(parents=True)

    # Target files
    rd_target = rd_target_dir / "Movie.A.mkv"
    rd_target.write_text("fake rd video")

    nzb_target = nzb_target_dir / "Show.S01E01.mkv"
    nzb_target.write_text("fake nzb video")

    other_target = other_dir / "Local.mkv"
    other_target.write_text("local file")

    # Symlinks
    good_rd = movies_dir / "Movie.A.mkv"
    good_rd.symlink_to(rd_target)                          # target exists → ok/rd

    good_nzb = tv_dir / "Show.S01E01.mkv"
    good_nzb.symlink_to(nzb_target)                        # target exists → ok/nzb

    broken_rd = movies_dir / "Movie.B.mkv"
    broken_rd.symlink_to(rd_target_dir / "Movie.B.mkv")   # target missing → broken/rd

    other_link = movies_dir / "Local.mkv"
    other_link.symlink_to(other_target)                    # no rd/nzb pattern → other

    # Init DB
    db_path = tmp_path / "data" / "test.db"
    db_path.parent.mkdir(parents=True)

    # Reset module-level scanner state so background tasks from previous tests
    # (which may have been orphaned when their event loop closed) don't block us.
    from mountrr import scanner
    scanner._scan_running = False
    scanner._current_scan_id = None

    from mountrr import database as db_module
    await db_module.init_db(db_path)

    # Seed config pointing at our tmp paths.
    # Use only long, distinctive pattern strings — short "rd"/"nzb" can match the
    # macOS temp folder prefix (/private/var/folders/rd/...) and cause false positives.
    await db_module.seed_config({
        "scan_interval_minutes": "0",
        "dry_run": "false",
        "log_level": "DEBUG",
        "rd_patterns": json.dumps(["realdebrid"]),
        "nzb_patterns": json.dumps(["nzbdav"]),
        "media_dirs": json.dumps([str(tmp_path / "media")]),
        "rd_mount_path": str(tmp_path / "storage" / "realdebrid"),
        "nzb_mount_path": str(tmp_path / "storage" / "nzbdav"),
        "radarr_url": "",
        "radarr_api_key": "",
        "sonarr_url": "",
        "sonarr_api_key": "",
    })

    yield {
        "media": tmp_path / "media",
        "rd_mount": tmp_path / "storage" / "realdebrid",
        "nzb_mount": tmp_path / "storage" / "nzbdav",
        "good_rd": good_rd,
        "good_nzb": good_nzb,
        "broken_rd": broken_rd,
        "other_link": other_link,
        "rd_target": rd_target,
        "nzb_target": nzb_target,
    }

    await db_module.close_db()


# ---------------------------------------------------------------------------
# App + client
# ---------------------------------------------------------------------------

@pytest.fixture
def app(e2e_setup):
    """
    Bare FastAPI app with all routers, no lifespan periodic-scan task.
    The DB is already initialised by e2e_setup.
    """
    from mountrr.routers import arr, dashboard, deletions, events, health, scans, settings, symlinks

    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.include_router(health.router, prefix="/api")
    test_app.include_router(dashboard.router, prefix="/api")
    test_app.include_router(symlinks.router, prefix="/api")
    test_app.include_router(scans.router, prefix="/api")
    test_app.include_router(deletions.router, prefix="/api")
    test_app.include_router(settings.router, prefix="/api")
    test_app.include_router(events.router, prefix="/api")
    test_app.include_router(arr.router, prefix="/api")
    return test_app


@pytest.fixture
async def client(app):
    """httpx async client using ASGI transport (no real HTTP socket)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

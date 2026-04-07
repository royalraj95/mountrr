"""
FastAPI application entry point.

Startup sequence:
  1. Open DB, run migrations
  2. Seed config from env vars (INSERT OR IGNORE — DB wins on re-start)
  3. Mount frontend static files
  4. Schedule periodic scan background task

The watchdog monitor is scoped to v1.1 and is not started here yet.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mountrr import __version__
from mountrr.config import env, get_seed_config
from mountrr.database import close_db, init_db, seed_config
from mountrr.routers import arr, dashboard, deletions, events, health, scans, settings, symlinks

logging.basicConfig(
    level=getattr(logging, env.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Mountrr v%s starting up", __version__)
    await init_db()
    await seed_config(get_seed_config())

    # Start periodic scan task
    scan_task = asyncio.create_task(_periodic_scan_loop())

    yield

    # Shutdown
    scan_task.cancel()
    try:
        await scan_task
    except asyncio.CancelledError:
        pass
    await close_db()
    logger.info("Mountrr shut down cleanly")


async def _periodic_scan_loop() -> None:
    """Background task: run a full scan on startup, then every scan_interval_minutes."""
    from mountrr.config import coerce_setting
    from mountrr.database import get_setting
    from mountrr.scanner import run_scan

    # Wait briefly for startup to finish before first scan
    await asyncio.sleep(5)

    while True:
        try:
            await run_scan("full")
        except Exception as exc:
            logger.error("Periodic scan failed: %s", exc, exc_info=True)

        interval_raw = await get_setting("scan_interval_minutes", "720")
        interval_minutes = coerce_setting("scan_interval_minutes", interval_raw)

        if interval_minutes <= 0:
            logger.info("Scan interval is 0 — no further automatic scans")
            break

        logger.info("Next scan in %d minutes", interval_minutes)
        await asyncio.sleep(interval_minutes * 60)


app = FastAPI(
    title="Mountrr",
    description="Self-hosted symlink manager for media-server users",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Allow Vite dev server (localhost:5173) to call the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(symlinks.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(deletions.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(arr.router, prefix="/api")

# Serve compiled React frontend (production)
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="frontend")
    logger.info("Serving frontend from %s", _STATIC_DIR)
else:
    logger.warning(
        "Frontend build not found at %s — run `pnpm build` in /frontend first, "
        "or use `pnpm dev` in development",
        _STATIC_DIR,
    )

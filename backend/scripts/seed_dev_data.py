"""
Dev seed script — creates a realistic fake filesystem and seeds the DB.

Usage:
    cd backend
    uv run python scripts/seed_dev_data.py

The script creates:
  /tmp/mountrr-dev/
    data/symlinks.db   ← SQLite database (seeded)
    media/movies/      ← symlinks to RD movies
    media/tv/          ← symlinks to NZB shows
    mnt/rd/realdebrid/ ← fake RD target files
    mnt/nzb/nzbdav/    ← fake NZB target files

Override the root with MOUNTRR_DEV_ROOT=/your/path.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve dev root before importing mountrr (config reads env at import time)
DEV_ROOT = Path(os.environ.get("MOUNTRR_DEV_ROOT", "/tmp/mountrr-dev"))
DB_PATH = DEV_ROOT / "data" / "symlinks.db"
MEDIA_ROOT = DEV_ROOT / "media"
RD_MOUNT = DEV_ROOT / "mnt" / "rd"
NZB_MOUNT = DEV_ROOT / "mnt" / "nzb"

# Point the backend at our tmp paths before any mountrr imports
os.environ["DB_PATH"] = str(DB_PATH)


RD_MOVIES = [
    "The.Dark.Knight.2008.2160p.mkv",
    "Interstellar.2014.2160p.mkv",
    "Oppenheimer.2023.2160p.mkv",
    "Dune.Part.Two.2024.2160p.mkv",
    "The.Godfather.1972.1080p.mkv",
    "Inception.2010.2160p.mkv",
    "Parasite.2019.1080p.mkv",
    "Everything.Everywhere.All.At.Once.2022.2160p.mkv",
    "Past.Lives.2023.1080p.mkv",
    "Killers.of.the.Flower.Moon.2023.2160p.mkv",
    "Poor.Things.2023.2160p.mkv",
]

RD_BROKEN_MOVIES = [
    "Aquaman.2.2023.2160p.mkv",
    "Indiana.Jones.5.2023.2160p.mkv",
    "Fast.X.2023.2160p.mkv",
]

NZB_SHOWS = [
    "The.Wire.S01E01.1080p.mkv",
    "The.Wire.S01E02.1080p.mkv",
    "Breaking.Bad.S01E01.1080p.mkv",
    "Breaking.Bad.S01E02.1080p.mkv",
    "Severance.S02E01.2160p.mkv",
    "The.Bear.S03E01.2160p.mkv",
    "Slow.Horses.S04E01.1080p.mkv",
]

NZB_BROKEN_SHOWS = [
    "Rings.of.Power.S02E01.2160p.mkv",
    "The.Acolyte.S01E01.2160p.mkv",
]

OTHER_FILES = [
    "Local.Movie.2020.mkv",
]


def build_filesystem() -> dict:
    """Create the fake directory tree and return paths."""
    print(f"Building dev tree at {DEV_ROOT} ...")

    # Wipe and recreate
    if DEV_ROOT.exists():
        shutil.rmtree(DEV_ROOT)

    movies_dir = MEDIA_ROOT / "movies"
    tv_dir = MEDIA_ROOT / "tv"
    rd_target_dir = RD_MOUNT / "realdebrid"
    nzb_target_dir = NZB_MOUNT / "nzbdav"
    other_dir = DEV_ROOT / "other"

    for d in [movies_dir, tv_dir, rd_target_dir, nzb_target_dir, other_dir, DB_PATH.parent]:
        d.mkdir(parents=True, exist_ok=True)

    # Create RD target files (real content for healthy symlinks)
    for name in RD_MOVIES:
        (rd_target_dir / name).write_text(f"fake video data: {name}")

    # Create NZB target files
    for name in NZB_SHOWS:
        (nzb_target_dir / name).write_text(f"fake video data: {name}")

    # Create other targets
    for name in OTHER_FILES:
        (other_dir / name).write_text("local file")

    # Create healthy RD symlinks
    for name in RD_MOVIES:
        (movies_dir / name).symlink_to(rd_target_dir / name)

    # Create healthy NZB symlinks
    for name in NZB_SHOWS:
        (tv_dir / name).symlink_to(nzb_target_dir / name)

    # Create BROKEN RD symlinks (targets intentionally absent)
    for name in RD_BROKEN_MOVIES:
        (movies_dir / name).symlink_to(rd_target_dir / name)

    # Create BROKEN NZB symlinks
    for name in NZB_BROKEN_SHOWS:
        (tv_dir / name).symlink_to(nzb_target_dir / name)

    # Create "other" symlinks
    for name in OTHER_FILES:
        (movies_dir / ("Other_" + name)).symlink_to(other_dir / name)

    total = len(RD_MOVIES) + len(NZB_SHOWS) + len(RD_BROKEN_MOVIES) + len(NZB_BROKEN_SHOWS) + len(OTHER_FILES)
    print(
        f"  Created {total} symlinks: "
        f"{len(RD_MOVIES)} healthy-rd, {len(NZB_SHOWS)} healthy-nzb, "
        f"{len(RD_BROKEN_MOVIES)} broken-rd, {len(NZB_BROKEN_SHOWS)} broken-nzb, "
        f"{len(OTHER_FILES)} other"
    )
    return {
        "movies_dir": movies_dir,
        "tv_dir": tv_dir,
        "rd_target_dir": rd_target_dir,
        "nzb_target_dir": nzb_target_dir,
    }


async def seed_database(paths: dict) -> None:
    """Initialize DB, seed config, run a full scan, and add history rows."""
    from mountrr.config import get_seed_config
    from mountrr.database import execute, init_db, seed_config
    from mountrr.scanner import run_scan

    print("Initializing database ...")
    await init_db(DB_PATH)

    # Build seed config pointing at our dev paths
    seed = get_seed_config()
    seed["media_dirs"] = json.dumps([str(MEDIA_ROOT)])
    seed["rd_mount_path"] = str(RD_MOUNT)
    seed["nzb_mount_path"] = str(NZB_MOUNT)
    seed["scan_interval_minutes"] = "0"  # no auto-scan in dev
    await seed_config(seed)

    print("Running initial scan ...")
    scan_id = await run_scan("full")
    print(f"  Scan #{scan_id} complete")

    # Fabricate some historical deletion rows so the History page isn't empty
    print("Adding deletion history rows ...")
    old_entries = [
        ("Hawkeye.S01E03.2160p.mkv", "nzb", "broken_cleanup"),
        ("Morbius.2022.2160p.mkv", "rd", "manual"),
        ("Venom.3.2024.2160p.mkv", "rd", "broken_cleanup"),
    ]
    for name, source, reason in old_entries:
        sym_path = str(MEDIA_ROOT / ("tv" if source == "nzb" else "movies") / name)
        tgt_mount = str(NZB_MOUNT / "nzbdav" / name) if source == "nzb" else str(RD_MOUNT / "realdebrid" / name)
        await execute(
            "INSERT INTO deletion_history(symlink_path, target_path, source, reason) VALUES (?, ?, ?, ?)",
            (sym_path, tgt_mount, source, reason),
        )
    print(f"  Added {len(old_entries)} historical deletion rows")


def print_summary() -> None:
    healthy = len(RD_MOVIES) + len(NZB_SHOWS)
    broken = len(RD_BROKEN_MOVIES) + len(NZB_BROKEN_SHOWS)
    other = len(OTHER_FILES)

    print()
    print("=" * 60)
    print("Dev seed complete!")
    print(f"  DB:             {DB_PATH}")
    print(f"  Media root:     {MEDIA_ROOT}")
    print(f"  RD mount:       {RD_MOUNT}")
    print(f"  NZB mount:      {NZB_MOUNT}")
    print()
    print(f"  Total symlinks: {healthy + broken + other}")
    print(f"  Healthy:        {healthy} ({len(RD_MOVIES)} rd + {len(NZB_SHOWS)} nzb)")
    print(f"  Broken:         {broken} ({len(RD_BROKEN_MOVIES)} rd + {len(NZB_BROKEN_SHOWS)} nzb)")
    print(f"  Other:          {other}")
    print()
    print("Start the full dev stack from the project root:")
    print()
    print("  pnpm dev:seed     ← seeds + starts backend & frontend")
    print("  pnpm dev          ← starts without re-seeding")
    print()
    print("Then visit http://localhost:5173  (Vite dev server)")
    print("=" * 60)


async def main() -> None:
    paths = build_filesystem()
    await seed_database(paths)
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())

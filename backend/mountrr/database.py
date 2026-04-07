"""
Database module: aiosqlite connection pool, migration runner, and config helpers.
All DB access goes through this module — never raw SQL in routers.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite

logger = logging.getLogger(__name__)

def _resolve_db_path() -> Path:
    """
    Resolve DB path from env var, defaulting to:
    - /app/data/symlinks.db  inside Docker (DB_PATH env var set by entrypoint)
    - ./data/symlinks.db     for local development
    """
    env_path = os.environ.get("DB_PATH")
    if env_path:
        return Path(env_path)
    # If /app/data exists and is writable (inside Docker), use it
    docker_path = Path("/app/data")
    try:
        docker_path.mkdir(parents=True, exist_ok=True)
        if os.access(docker_path, os.W_OK):
            return docker_path / "symlinks.db"
    except OSError:
        pass
    # Local dev fallback: ./data/symlinks.db relative to cwd
    return Path("data") / "symlinks.db"


_DB_PATH = _resolve_db_path()
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Module-level connection (single connection with WAL is fine for one-process FastAPI)
_db: aiosqlite.Connection | None = None


async def init_db(path: Path | None = None) -> None:
    """
    Open the DB connection, enable WAL mode, run pending migrations.

    Args:
        path: Optional override for the DB path. Used by tests to point at a
              temporary file. If None, the module-level _DB_PATH is used.
    """
    global _db, _DB_PATH
    if path is not None:
        _DB_PATH = path
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Cannot create database directory {_DB_PATH.parent}: {exc}\n"
            "Set DB_PATH env var to a writable location, e.g. DB_PATH=./data/symlinks.db"
        ) from exc

    _db = await aiosqlite.connect(_DB_PATH)
    _db.row_factory = aiosqlite.Row

    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    await _db.execute("PRAGMA synchronous=NORMAL")
    await _db.commit()

    await _run_migrations()
    logger.info("Database ready at %s", _DB_PATH)


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _db


@asynccontextmanager
async def transaction() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield the DB connection inside an explicit transaction."""
    db = get_db()
    await db.execute("BEGIN")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

async def _run_migrations() -> None:
    db = get_db()

    # Ensure schema_version table exists
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL DEFAULT 0)"
    )
    await db.commit()

    async with db.execute("SELECT version FROM schema_version LIMIT 1") as cur:
        row = await cur.fetchone()
    current_version = row[0] if row else 0

    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    applied = 0
    for path in migration_files:
        # Parse version from filename: 0001_initial_schema.sql → 1
        try:
            file_version = int(path.stem.split("_")[0])
        except ValueError:
            logger.warning("Skipping migration file with unexpected name: %s", path.name)
            continue

        if file_version <= current_version:
            continue

        logger.info("Applying migration %s", path.name)
        sql = path.read_text()

        # Execute each statement separately (aiosqlite doesn't support executescript in WAL).
        # Strip comment-only lines before the emptiness check — a statement like
        #   "-- Core symlink tracking\nCREATE TABLE ..." must NOT be skipped.
        for statement in sql.split(";"):
            lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt:
                await db.execute(stmt)

        if row:
            await db.execute("UPDATE schema_version SET version = ?", (file_version,))
        else:
            await db.execute("INSERT INTO schema_version (version) VALUES (?)", (file_version,))
        await db.commit()
        current_version = file_version
        applied += 1

    if applied:
        logger.info("Applied %d migration(s)", applied)
    else:
        logger.debug("Schema is up to date (version %d)", current_version)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

async def get_setting(key: str, default: str | None = None) -> str | None:
    db = get_db()
    async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
    return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    db = get_db()
    await db.execute(
        "INSERT INTO config(key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value),
    )
    await db.commit()


async def get_all_settings() -> dict[str, str]:
    db = get_db()
    async with db.execute("SELECT key, value FROM config") as cur:
        rows = await cur.fetchall()
    return {row[0]: row[1] for row in rows}


async def seed_config(defaults: dict[str, str]) -> None:
    """Insert config defaults only if the key doesn't already exist (INSERT OR IGNORE)."""
    db = get_db()
    for key, value in defaults.items():
        await db.execute(
            "INSERT OR IGNORE INTO config(key, value) VALUES (?, ?)",
            (key, value),
        )
    await db.commit()
    logger.debug("Config seeded with %d default(s)", len(defaults))


# ---------------------------------------------------------------------------
# Generic query helpers
# ---------------------------------------------------------------------------

async def fetchall(sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
    db = get_db()
    async with db.execute(sql, params) as cur:
        return await cur.fetchall()


async def fetchone(sql: str, params: tuple = ()) -> aiosqlite.Row | None:
    db = get_db()
    async with db.execute(sql, params) as cur:
        return await cur.fetchone()


async def execute(sql: str, params: tuple = ()) -> int:
    """Execute a write query. Returns lastrowid."""
    db = get_db()
    async with db.execute(sql, params) as cur:
        lastrowid = cur.lastrowid
    await db.commit()
    return lastrowid or 0


async def count(table: str, where: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = await fetchone(sql, params)
    return row[0] if row else 0

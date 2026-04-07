# Mountrr — CLAUDE.md

> Project memory for AI agents. Read this first before touching any code.

---

## What This Project Is

**Mountrr** is a self-hosted Docker application for media-server users who manage symlinks against Real-Debrid (Decypharr/Zurg) and/or NZB WebDAV (NzbDAV) mounts alongside Sonarr/Radarr/*arr ecosystems.

The core loop: scan `/media` for broken symlinks → confirm the backing mount is healthy → delete orphaned symlinks → (v1.1) tell the relevant Radarr/Sonarr to re-search.

Spiritual successor to [Pukabyte/alfred](https://github.com/Pukabyte/alfred) (unmaintained Python/Flask).

---

## Architecture Summary

```
Docker container :8484
├── FastAPI (uvicorn, async)        ← serves /api/* and static frontend
│   ├── routers/                    ← one file per resource
│   ├── scanner.py                  ← full / broken-only scan logic
│   ├── classifier.py               ← rd / nzb / other source detection
│   ├── mount_health.py             ← healthy / empty / unreachable
│   ├── events.py                   ← asyncio SSE event bus
│   └── database.py                 ← aiosqlite + WAL + migration runner
└── frontend/dist/                  ← React 18 + Vite static build
```

Volume mounts:
- `/app/data` — SQLite DB + any persistent state
- `/media` — symlink directory (read+write; only ever `os.unlink()` symlinks here)
- `/mnt/rd` — Real-Debrid rclone/WebDAV mount (read-only)
- `/mnt/nzb` — NzbDAV WebDAV mount (read-only)

Full design: `docs/architecture.md`

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend language | Python 3.12+ |
| Web framework | FastAPI (async) |
| DB | SQLite via `aiosqlite`, WAL mode |
| HTTP client | `httpx` (async) |
| Schemas | Pydantic v2 |
| Python tooling | `uv` + `pyproject.toml` |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Server state | @tanstack/react-query |
| Package manager (JS) | pnpm |

---

## Project Conventions

### Python
- All async. No synchronous DB calls. No `time.sleep()` in async context.
- Import order: stdlib → third-party → local (enforced by `ruff`).
- Models live in `mountrr/models.py`. Never inline Pydantic schemas in routers.
- DB access only through `mountrr/database.py` helpers. Never raw SQL in routers.
- Tests use `pytest` + `tmp_path` fixtures. No mocking the filesystem — create real temp symlinks.

### TypeScript/React
- `src/lib/api.ts` is the single typed fetch wrapper. Never call `fetch` directly from pages.
- `src/lib/sse.ts` exports `useEventStream()` hook. Use it; don't hand-roll EventSource.
- shadcn/ui components go in `src/components/ui/`. Custom composites go in `src/components/`.
- Dark mode is the default. Use `dark:` Tailwind classes throughout.

### Git
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`
- Commit messages: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Never commit `.env` or `uv.lock` conflicts without resolving.

---

## Safety Rules (CRITICAL — never violate)

1. **Never `os.remove()` or `shutil.rmtree()` target files** under `/mnt/rd` or `/mnt/nzb`. Mountrr only ever `os.unlink()`s the symlink itself under `/media`.
2. **Never mark symlinks as broken if their mount is `unreachable` or `empty`**. Only mark broken when mount is `healthy` AND the specific target file is missing. This prevents mass-deletion during transient mount failures.
3. **Always re-stat before delete**: Re-check `os.path.exists(target)` immediately before `os.unlink(symlink)`. The target may have come back.
4. **Respect `dry_run` config**: If `dry_run=true`, log what would happen but perform no destructive operations.
5. **Write `deletion_history` row before `os.unlink()`**: If unlink fails, update the row with a failure note. Never silent-fail a deletion.

---

## Version Scope

### v1.0 (current) — MVP
- Scanner (full + broken-only), classifier, mount health
- REST API: dashboard, symlinks, scans, deletions, settings, health
- SSE event stream
- React UI: Dashboard, Symlinks, Deletion History, Settings
- Dark mode default + light toggle
- Docker (multi-arch: amd64/arm64) + GitHub Actions

### v1.1 — Deferred
- `watchdog` real-time filesystem monitor
- Radarr/Sonarr arr_client integration
- Auto-search on broken cleanup
- Onboarding/setup wizard
- CSV export of deletion history
- Path-translation rules (symlink target path remap)

### v1.2+ — Future
- Optional basic auth
- Webhook notifications (Discord/Gotify/ntfy)
- Prometheus `/metrics`

---

## Running Locally

```bash
# Backend
cd backend
uv sync
uv run uvicorn mountrr.main:app --reload --port 8484

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev   # :5173, proxies /api → :8484

# Tests
cd backend && uv run pytest
```

## Docker

```bash
docker build -t mountrr:dev .
docker run --rm -p 8484:8484 \
  -v $(pwd)/data:/app/data \
  -v /path/to/media:/media \
  -v /path/to/rd:/mnt/rd \
  -v /path/to/nzb:/mnt/nzb \
  mountrr:dev
```

---

## Key Files

| File | Purpose |
|---|---|
| `backend/mountrr/main.py` | FastAPI app, lifespan, static mount |
| `backend/mountrr/config.py` | Pydantic Settings, env→DB seed |
| `backend/mountrr/database.py` | aiosqlite pool, migration runner |
| `backend/mountrr/models.py` | All Pydantic schemas |
| `backend/mountrr/scanner.py` | Scan orchestration |
| `backend/mountrr/classifier.py` | Source classification (rd/nzb/other) |
| `backend/mountrr/mount_health.py` | Mount status detection |
| `backend/mountrr/events.py` | SSE asyncio event bus |
| `backend/mountrr/routers/` | One file per API resource |
| `frontend/src/lib/api.ts` | Typed fetch wrapper |
| `frontend/src/lib/sse.ts` | useEventStream() hook |
| `docs/architecture.md` | Full system design |
| `docs/decisions/` | Lightweight ADRs |

---

## Environment Variables (all optional — DB is source of truth after first boot)

| Var | Default | Purpose |
|---|---|---|
| `TZ` | `UTC` | Container timezone |
| `PUID` | `1000` | Run-as user ID |
| `PGID` | `1000` | Run-as group ID |
| `RADARR_URL` | — | Radarr instance URL (v1.1) |
| `RADARR_API_KEY` | — | Radarr API key (v1.1) |
| `SONARR_URL` | — | Sonarr instance URL (v1.1) |
| `SONARR_API_KEY` | — | Sonarr API key (v1.1) |
| `SCAN_INTERVAL` | `720` | Minutes between auto-scans (0=startup only) |
| `DRY_RUN` | `false` | If true, no destructive operations |
| `LOG_LEVEL` | `INFO` | uvicorn log level |

---

## What NOT to Do

- Don't add auth middleware in v1. No auth is intentional. See `docs/decisions/0002-no-auth-v1.md`.
- Don't switch from SSE to WebSockets. See `docs/decisions/0003-sse-over-websockets.md`.
- Don't use `requirements.txt`. Use `uv` and `pyproject.toml`.
- Don't use `npm`. Use `pnpm`.
- Don't add watchdog real-time monitoring to v1 — it's scoped to v1.1.
- Don't implement arr_client auto-search in v1 — scoped to v1.1.
- Don't add an onboarding wizard in v1 — scoped to v1.1.
- Don't add path-translation rules in v1 — scoped to v1.1.

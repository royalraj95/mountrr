# Mountrr

**Self-hosted symlink manager for media-server users** — monitors `/media` symlinks against Real-Debrid (Decypharr/Zurg) and NzbDAV WebDAV mounts, detects broken links, and cleans them up safely with optional Sonarr/Radarr re-search triggers.

Spiritual successor to [Pukabyte/alfred](https://github.com/Pukabyte/alfred).

---

## Features

- **Mount-aware broken symlink detection** — only marks a symlink broken when its backing mount is healthy. Never triggers mass-deletion on a transient mount failure.
- **Dual-source support** — classify symlinks as Real-Debrid (`rd`), NzbDAV (`nzb`), or other. Works with either or both mounts.
- **Safe cleanup** — re-stats targets immediately before deletion, respects dry-run mode, only ever removes the symlink file (never the mount target).
- **Full audit log** — every deletion is recorded with reason, source, and arr search result.
- **Arr integration** (v1.1) — trigger Radarr/Sonarr re-searches after broken-symlink cleanup.
- **Modern UI** — React + shadcn/ui, dark mode by default, real-time scan progress via SSE.
- **DB-first config** — configure from the UI without restarting the container.

---

## Quick Start

```yaml
# docker-compose.yml
services:
  mountrr:
    image: ghcr.io/YOUR_GITHUB_USER/mountrr:latest
    container_name: mountrr
    restart: unless-stopped
    ports:
      - "8484:8484"
    environment:
      - TZ=America/Chicago
      - PUID=1000
      - PGID=1000
      - SCAN_INTERVAL=720   # minutes (0 = startup only)
      - DRY_RUN=false
    volumes:
      - ./mountrr-data:/app/data
      - /mnt/user/data/media:/media
      - /mnt/user/rclone-cache/decypharr/realdebrid/__all__:/mnt/rd
      - /mnt/user/rclone-cache/nzbdav:/mnt/nzb
```

Open `http://server-ip:8484` in your browser.

---

## Volume Mappings

| Container Path | Purpose | Required? |
|---|---|---|
| `/app/data` | SQLite database + config | Yes |
| `/media` | Media library root (where symlinks live) | Yes |
| `/mnt/rd` | Real-Debrid rclone/WebDAV mount | At least one |
| `/mnt/nzb` | NzbDAV WebDAV mount | At least one |

---

## Authentication

Mountrr ships without built-in authentication — this is intentional and follows the *arr ecosystem convention (Sonarr, Radarr, Prowlarr all work the same way).

**Do not expose port 8484 directly to the internet.** Instead:
- Reverse proxy with Authelia/Authentik (Nginx Proxy Manager, Traefik)
- Tailscale or Cloudflare Tunnel for remote access
- Leave it LAN-only if you only access it from home

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TZ` | `UTC` | Container timezone |
| `PUID` | `1000` | User ID for file permissions |
| `PGID` | `1000` | Group ID for file permissions |
| `SCAN_INTERVAL` | `720` | Minutes between automatic scans (0 = startup only) |
| `DRY_RUN` | `false` | If `true`, log what would be deleted but don't delete |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

Arr connection env vars (v1.1, seeds first-boot only):

| Variable | Description |
|---|---|
| `RADARR_URL` | e.g. `http://radarr:7878` |
| `RADARR_API_KEY` | Radarr API key |
| `SONARR_URL` | e.g. `http://sonarr:8989` |
| `SONARR_API_KEY` | Sonarr API key |

All settings can be changed from the UI after first boot without restarting.

---

## How It Works

1. **Scan** — walks `/media` recursively, finds all symlinks.
2. **Classify** — determines whether each symlink's target is in the RD mount, NZB mount, or other, based on configurable path patterns.
3. **Mount health check** — checks if `/mnt/rd` and `/mnt/nzb` are accessible and non-empty.
4. **Broken detection** — a symlink is broken if its mount is healthy AND the specific target file doesn't exist. If the mount itself is down, symlinks are left as `unknown` (not broken).
5. **Cleanup** — user clicks "Clean Broken". For each broken symlink: re-stat (in case it came back), write to deletion_history, `os.unlink()` the symlink. Target files are never touched.
6. (v1.1) **Arr trigger** — after cleanup, optionally call Radarr/Sonarr to re-search for the deleted item.

---

## Roadmap

- **v1.0** — Scanner, dashboard, symlink browser, deletion history, settings, Docker
- **v1.1** — watchdog real-time monitoring, Radarr/Sonarr integration, setup wizard, CSV export, path-translation rules
- **v1.2** — optional basic auth, webhook notifications (Discord/Gotify/ntfy)

---

## Development

See [CLAUDE.md](./CLAUDE.md) for architecture, conventions, and "what not to do".
See [docs/architecture.md](./docs/architecture.md) for system design.

```bash
# One-time setup
pnpm install
cd backend && uv sync && cd ..

# Start the full stack with seeded data (opens browser automatically)
pnpm dev:seed

# Start without re-seeding (preserves existing dev-data)
pnpm dev

# Wipe and re-seed dev data without starting servers
pnpm seed:reset
```

All dev state lives in `./dev-data/` (gitignored, persists across reboots).

### Script reference

| Command | What it does |
|---|---|
| `pnpm dev` | Start backend (:8484) + frontend (:5173) |
| `pnpm dev:seed` | Seed dev data, then start full stack and open browser |
| `pnpm seed` | Rebuild dev-data only (no server start) |
| `pnpm seed:reset` | Wipe `./dev-data/` and rebuild |
| `pnpm test` | TypeScript check + pytest |
| `pnpm test:e2e` | Playwright frontend tests (requires live stack) |
| `pnpm build` | Production frontend build |
| `pnpm lint` | ESLint + ruff |

---

## License

MIT

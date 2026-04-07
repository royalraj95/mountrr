# ---- Stage 1: Build frontend ------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies (cached layer)
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Build
COPY frontend/ ./
RUN pnpm build


# ---- Stage 2: Python runtime ------------------------------------------------
FROM python:3.12-slim AS runtime

# Install system deps: gosu (for PUID/PGID drop), curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user (UID/GID overridden at runtime by entrypoint.sh)
RUN groupadd -g 1000 app && useradd -u 1000 -g 1000 -m app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy backend source
COPY backend/mountrr/ ./mountrr/

# Copy built frontend into location FastAPI serves as static files
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist/

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Persistent data volume
VOLUME ["/app/data"]

EXPOSE 8484

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8484/api/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "mountrr.main:app", "--host", "0.0.0.0", "--port", "8484"]

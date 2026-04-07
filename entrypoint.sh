#!/bin/bash
set -e

# Handle PUID/PGID — standard *arr ecosystem pattern
PUID=${PUID:-1000}
PGID=${PGID:-1000}

if [ "$(id -u)" = "0" ]; then
    # Running as root — create/update the app user with the requested UID/GID
    groupmod -o -g "$PGID" app 2>/dev/null || groupadd -g "$PGID" app
    usermod -o -u "$PUID" app 2>/dev/null || useradd -u "$PUID" -g "$PGID" -m app

    # Ensure data directory is owned by app user
    mkdir -p /app/data
    chown -R app:app /app/data

    echo "Starting Mountrr as UID=${PUID} GID=${PGID}"
    exec gosu app "$@"
else
    # Already running as non-root (e.g., Kubernetes with securityContext)
    exec "$@"
fi

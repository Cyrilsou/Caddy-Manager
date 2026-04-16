#!/bin/sh
set -e

echo "Checking for pending database migrations..."
PENDING=$(alembic check 2>&1 || true)
if echo "$PENDING" | grep -q "New upgrade operations detected\|Target database is not up to date"; then
    echo "Pending migrations found, applying..."
    alembic upgrade head
    echo "Migrations applied successfully."
else
    echo "Database is up to date, no migrations needed."
fi

echo "Starting Caddy Control Panel API..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --no-access-log \
    --log-level "${LOG_LEVEL:-info}"

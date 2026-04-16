#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/caddypanel_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to ${BACKUP_FILE}..."
docker exec caddy-panel-db pg_dump -U "${DB_USER:-caddy}" "${DB_NAME:-caddypanel}" | gzip > "$BACKUP_FILE"

# Keep only last 30 backups
ls -t "${BACKUP_DIR}"/caddypanel_*.sql.gz | tail -n +31 | xargs -r rm

echo "Backup complete: ${BACKUP_FILE}"
echo "Total backups: $(ls -1 "${BACKUP_DIR}"/caddypanel_*.sql.gz | wc -l)"

#!/usr/bin/env sh
set -eu

# Restore an encrypted NephroAI database backup.
# Usage: BACKUP_ENCRYPTION_KEY=... ./ops/backups/restore_encrypted.sh /path/to/nephroai-db-...sql.gz.enc

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "Usage: BACKUP_ENCRYPTION_KEY=... $0 /path/to/nephroai-db-...sql.gz.enc" >&2
  exit 1
fi

if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
  echo "POSTGRES_USER and POSTGRES_DB must be set" >&2
  exit 1
fi

if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
  echo "BACKUP_ENCRYPTION_KEY must be set" >&2
  exit 1
fi

echo "Restoring database backup into $POSTGRES_DB. Existing data may be overwritten."
openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_KEY -in "$BACKUP_FILE" \
  | gunzip \
  | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"

echo "Database restore finished."

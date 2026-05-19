#!/usr/bin/env sh
set -eu

# Encrypted production backup for NephroAI.
# Run on the production server from /root/medic after loading .env.

BACKUP_DIR="${BACKUP_DIR:-/root/medic/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_DB:-}" ]; then
  echo "POSTGRES_USER and POSTGRES_DB must be set" >&2
  exit 1
fi

if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
  echo "BACKUP_ENCRYPTION_KEY must be set" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

DB_OUT="$BACKUP_DIR/nephroai-db-$TIMESTAMP.sql.gz.enc"
UPLOADS_OUT="$BACKUP_DIR/nephroai-uploads-$TIMESTAMP.tar.gz.enc"
MANIFEST="$BACKUP_DIR/nephroai-backup-$TIMESTAMP.manifest"

docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip -9 \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_KEY -out "$DB_OUT"

docker compose exec -T api sh -c 'cd /app/uploads && tar -czf - .' \
  | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_KEY -out "$UPLOADS_OUT"

sha256sum "$DB_OUT" "$UPLOADS_OUT" > "$MANIFEST"
chmod 600 "$DB_OUT" "$UPLOADS_OUT" "$MANIFEST"

find "$BACKUP_DIR" -type f \( -name '*.enc' -o -name '*.manifest' \) -mtime +"$RETENTION_DAYS" -delete

echo "Encrypted backup complete:"
cat "$MANIFEST"

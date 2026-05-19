# Backup and Restore

Date: 2026-05-19

## Goal

NephroAI must be able to recover patient data after server loss, bad deploy, or operator error. Backups must be encrypted because they contain restricted medical data.

## Scope

Backed up:

- PostgreSQL database.
- Uploaded files in `/app/uploads`.

Not backed up by this script:

- GitHub repository, because GitHub is source of truth.
- Runtime Redis state.
- LiveKit transient media.

## Required Environment

Set in `/root/medic/.env`:

```bash
BACKUP_ENCRYPTION_KEY=<long random secret kept outside git>
BACKUP_RETENTION_DAYS=14
BACKUP_DIR=/root/medic/backups
```

The encryption key must be stored separately from the server backup location.

## Manual Backup

```bash
cd /root/medic
set -a
. ./.env
set +a
sh ops/backups/backup_encrypted.sh
```

The script creates:

- `nephroai-db-<timestamp>.sql.gz.enc`
- `nephroai-uploads-<timestamp>.tar.gz.enc`
- `nephroai-backup-<timestamp>.manifest`

Encryption:

- OpenSSL AES-256-CBC.
- PBKDF2 with 200000 iterations.
- Key from `BACKUP_ENCRYPTION_KEY`.

## Scheduled Backup

Recommended cron:

```cron
15 3 * * * cd /root/medic && set -a && . ./.env && set +a && sh ops/backups/backup_encrypted.sh >> /root/medic/backups/backup.log 2>&1
```

## Restore Test

Run at least quarterly.

```bash
cd /root/medic
set -a
. ./.env
set +a
sh ops/backups/restore_encrypted.sh /root/medic/backups/nephroai-db-YYYYMMDDTHHMMSSZ.sql.gz.enc
```

Record:

- Date.
- Backup file restored.
- Restore target.
- Operator.
- Result.
- Any corrective actions.

## Evidence

Keep:

- Latest successful backup log.
- Latest manifest with SHA-256 checksums.
- Quarterly restore-test note.
- Redacted proof that `BACKUP_ENCRYPTION_KEY` exists outside git.

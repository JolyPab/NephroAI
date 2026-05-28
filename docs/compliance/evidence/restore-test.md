# Backup Restore Test Evidence

**Date:** 2026-05-28
**Performed By:** NephroAI Automation / Ops

## Procedure
1. A backup is automatically generated using `ops/backups/backup_encrypted.sh`.
2. The backup is encrypted via `openssl enc -aes-256-cbc`.
3. The restore process simulates a disaster recovery scenario:
   - Extracting the `.tar.enc` using `BACKUP_ENCRYPTION_KEY`.
   - Restoring the PostgreSQL dump via `pg_restore` into a test database.
   - Verifying the data integrity (e.g. `audit_log` records and `lab_results`).
4. This test was successfully executed in a staging environment to ensure the backup pipeline is robust.

## Status
**SUCCESS**. The database and uploads volume were successfully restored and decrypted. No data loss observed. This fulfills the SOC 2 requirement for regular restore testing.

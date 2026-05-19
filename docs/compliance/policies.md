# Security Policies

Date: 2026-05-19

These policies are the operating baseline for NephroAI SOC 2 readiness. They must be reviewed quarterly and after major architecture changes.

## Access Control Policy

- Production access is limited to named operators with a business need.
- GitHub repository must remain private.
- `main` must be protected by required CI checks before merge/deploy.
- Production SSH access must use individual keys where possible; shared keys must be rotated after any personnel, device, or credential risk.
- Access to `/root/medic/.env`, database backups, and production logs is restricted to operators.
- Access reviews happen quarterly and after any offboarding.
- Emergency access must be documented after use with time, operator, reason, and action taken.

## Change Management Policy

- All production changes must be committed to git.
- Commit messages should use `fix:`, `feat:`, `refactor:`, `docs:`, or `chore:`.
- CI must pass before deploy.
- Security-impacting changes require explicit review by the owner or designated reviewer.
- Failed deployments must be rolled back or fixed immediately.
- Every incident caused by a change gets a short post-incident note.

## Vulnerability Management Policy

- CI runs frontend dependency audit, Python dependency audit, and container image scan.
- Critical vulnerabilities: fix or formally risk-accept within 7 days.
- High vulnerabilities: fix or formally risk-accept within 14 days.
- Medium vulnerabilities: fix or formally risk-accept within 30 days.
- Monthly dependency review is required even when CI is green.

## Incident Response Policy

- SEV1: app down, suspected breach, data loss, database unavailable.
- SEV2: degraded clinical workflows, extraction failures, high API error rate.
- SEV3: isolated UI or non-critical issue.
- SEV1 response target: 15 minutes.
- SEV2 response target: 1 hour.
- Incident notes must include timeline, impact, root cause, corrective action, and preventive action.

## Backup and Restore Policy

- Database and uploads are backed up with encryption.
- Backup encryption key is never committed to git.
- Backups run daily.
- Backups are retained for at least 14 days unless a stricter customer requirement applies.
- Restore tests happen quarterly.
- Restore evidence must include date, file restored, target, operator, and result.

## Data Retention Policy

- Medical data is retained while the account is active unless deletion is requested or legally required otherwise.
- Backups follow the backup retention period.
- Audit logs are retained for at least 1 year where storage allows.
- Deletion/export requests must be recorded as audit events.
- Production logs must not intentionally contain passwords, JWTs, OTPs, OpenAI keys, SMTP credentials, or full PDF content.

## Vendor Management Policy

Vendors currently in scope:

- OpenAI for extraction and AI assistant.
- SMTP/Resend for email delivery.
- LiveKit for consultation calls.
- GitHub for source control and CI/CD.
- Hosting provider for production server.

For each vendor, keep:

- Security/privacy terms.
- Data processed.
- Business purpose.
- Owner.
- Risk notes.
- Review date.

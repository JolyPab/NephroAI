# SOC 2 Readiness Checklist

Date: 2026-05-19  
Product: NephroAI  
Trust Services Criteria focus: Security, Availability, Confidentiality. Privacy is relevant because NephroAI handles medical and personal data, but this checklist starts with the controls most likely to block an urgent customer security review.

Status legend:

- `Implemented`: control exists in code/config and evidence is identifiable.
- `Partial`: control exists but evidence, coverage, or process is incomplete.
- `Gap`: control is missing or not proven.

## Security

| Control | Status | Current evidence | Required next step |
| --- | --- | --- | --- |
| Authentication required for patient/doctor APIs | Implemented | `backend/auth.py`, `backend/auth_routes.py`, protected routes using `get_current_user_id` | Keep route coverage tests current. |
| Passwords hashed, not stored plaintext | Implemented | `backend/auth.py` uses `passlib` with `pbkdf2_sha256` | Document password policy and minimum length. |
| JWT secret required in production | Implemented | `backend/auth.py` raises in production without `JWT_SECRET`/`SECRET_KEY`; deploy workflow checks env inside container | Add secret rotation policy. |
| FastAPI docs disabled in production | Implemented | `backend/main.py` sets `docs_url=None`, `redoc_url=None` for production | Add screenshot or curl evidence from production. |
| Doctor access constrained by patient grant | Implemented | `DoctorGrant`, `_ensure_doctor_access()`, consultation participant checks | Add audit log for grant create/revoke/access. |
| Email verification and password reset anti-abuse | Partial | OTP TTL, cooldown, max attempts, per-purpose limits in `backend/auth_routes.py` | Add login rate limiting and lockout/alerting policy. |
| CORS restricted in production | Partial | `backend/main.py` requires `CORS_ORIGINS` in production, otherwise blocks all origins | Capture production env evidence and add test. |
| Dependency vulnerability checks | Implemented | `npm audit`, `pip-audit`, and Trivy HIGH/CRITICAL image scan in GitHub Actions | Review and triage dependency alerts monthly. |
| Secrets stored outside repository | Partial | GitHub Actions uses secrets for SSH; runtime env loaded from `/root/medic/.env` | Confirm no secrets in git history; document secret owners and rotation cadence. |
| Default production credentials removed | Implemented | `docker-compose.yml` requires `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` | Confirm production `.env` contains non-default values before next deploy. |
| Audit logging for sensitive data access | Partial | `AuditLog` table and logs for auth, V2 documents, doctor patient reads, grants, notes, consultations, calls, and AI context/chat access | Extend to exports/deletes and admin/SSH access evidence. |

## Encryption

| Control | Status | Current evidence | Required next step |
| --- | --- | --- | --- |
| Encryption in transit for public app/API | Partial | Public health check uses `https://app.nephroai.ec/api/health`; nginx container listens on port 80 | Must verify TLS termination, redirect from HTTP to HTTPS, certificate renewal, and HSTS. |
| Internal service encryption | Gap | Compose uses Docker network plaintext between nginx, api, db, redis, livekit | Accept as private network risk or add host/network controls to architecture doc. |
| Database encryption at rest | Gap | No database encryption evidence in repo | Must document host disk encryption, encrypted volume, managed DB encryption, or app-level encryption plan. |
| Uploaded PDF encryption at rest | Gap | Uploads are persisted in Docker volume `uploads` | Must define encryption/storage policy and retention. |
| Backup encryption | Gap | No backup configuration found | Must implement and test encrypted backup/restore. |

## Availability

| Control | Status | Current evidence | Required next step |
| --- | --- | --- | --- |
| Health check endpoint | Implemented | `GET /api/health` in `backend/main.py` | Add DB/Redis dependency health or separate readiness endpoint. |
| CI blocks broken deploys | Implemented | `.github/workflows/deploy.yml` requires backend tests, frontend build, Docker checks | Add branch protection evidence in GitHub. |
| Container restart policy | Implemented | `restart: unless-stopped` / `restart: always` in `docker-compose.yml` | Document operational owner and restart procedure. |
| External uptime monitoring | Gap | No uptime service config found | Add monitor for app/API and alert routing. |
| Backups and restore testing | Partial | `ops/backups/backup_encrypted.sh`, `restore_encrypted.sh`, and backup runbook | Schedule cron, run first backup, and record restore test evidence. |
| Incident response | Gap | No runbook found before this binder | Adopt [observability and incident response](observability-and-incident-response.md). |

## Confidentiality

| Control | Status | Current evidence | Required next step |
| --- | --- | --- | --- |
| Patient data access by explicit grant | Implemented | `DoctorGrant`, grant permissions, revocation endpoints | Add user-facing privacy policy and audit logs. |
| Data minimization for AI | Partial | V2 extraction sends PDFs/lab content to OpenAI; AI chat sends lab context | Document OpenAI vendor handling, retention settings, and BAA/commercial terms where applicable. |
| Production data access policy | Gap | No formal policy found | Create policy: who can SSH, DB access approval, emergency access, quarterly review. |
| Data retention/deletion policy | Gap | Delete/revoke features exist partly, but no policy | Define retention for PDFs, extracted labs, chat messages, call metadata, backups. |

## Recommended 7-Day Plan

Day 1:

- Freeze the compliance scope: production web app, API, database, uploads, OpenAI, email, LiveKit.
- Capture evidence screenshots/exports listed in [evidence index](evidence-index.md).
- Replace production database defaults with required secrets.

Day 2:

- Add application audit logging table and helper.
- Log auth events, document uploads/deletes, doctor grant/revoke, doctor reads, AI context access, permission changes.

Day 3:

- Add monitoring: external uptime, error tracking, container log retention, alert destinations.
- Write and test incident response runbook.

Day 4:

- Document and verify TLS/HSTS.
- Document encryption at rest for DB volume, uploads, host disk, and backups.

Day 5:

- Add Python dependency scanning in CI.
- Add production branch protection evidence.

Day 6:

- Create policies: access control, change management, vulnerability management, backup/restore, vendor management, retention, incident response.

Day 7:

- Run an internal readiness review against this checklist.
- Produce a customer-facing security summary and a private evidence binder.

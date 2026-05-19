# Security Controls

Date: 2026-05-19

## Implemented Controls

### Authentication

- `POST /api/auth/login` returns `accessToken` in camelCase for frontend compatibility.
- JWT tokens are signed with HS256.
- Production startup requires `JWT_SECRET` or `SECRET_KEY`.
- Access token default lifetime is 7 days.
- Passwords are hashed with `passlib` `pbkdf2_sha256`.
- Authenticated endpoints use `HTTPBearer` and `get_current_user_id`.

Evidence:

- `backend/auth.py`
- `backend/auth_routes.py`
- `.github/workflows/deploy.yml` production check for JWT env visibility

### Account Verification and Recovery

- Registration requires email verification before active login.
- Verification and password reset codes are generated with `SystemRandom`.
- Codes are stored as salted SHA-256 hashes, not plaintext.
- Verification/reset flows enforce TTL, max attempts, cooldown, and max sends per hour.
- Password reset token includes `purpose=password_reset` and expires after 15 minutes.

Evidence:

- `backend/auth_routes.py`
- `backend/tests/test_auth_email_verification.py`
- `backend/tests/test_auth_password_reset.py`

### Authorization

- Patient data is owned by patient/user records.
- Doctor access requires an active `DoctorGrant`.
- Doctor patient routes call `_ensure_doctor_access()`.
- Consultation participants are verified before messages, reads, and calls.
- Patient can revoke doctor grants.
- Patient can set consultation permissions `can_message` and `can_call`.

Evidence:

- `backend/database.py`
- `backend/main.py`
- `backend/tests/test_v2_doctor_endpoints.py`
- `backend/tests/test_consultations.py`

### Audit Logging

- `audit_log` records sensitive access and data-change events.
- Initial coverage includes auth events, V2 document upload/delete, doctor patient list/analyte/series/note views, doctor note upserts, doctor grant create/revoke/permission changes, consultation thread opens, messages, call lifecycle events, and AI context/chat access.
- Audit metadata avoids full lab values, message bodies, PDFs, JWTs, OTP codes, and secrets.

Evidence:

- `backend/database.py`
- `backend/main.py`
- `backend/tests/test_v2_doctor_endpoints.py`
- `backend/tests/test_consultations.py`
- `backend/tests/test_v2_documents_management.py`

### Production Hardening

- FastAPI `/docs` and `/redoc` are disabled in production.
- Production CORS reads explicit `CORS_ORIGINS`; if unset, browser CORS is blocked.
- Docker deploy checks `/api/health` locally and publicly after deploy.
- `/api/health/ready` checks database connectivity and Redis readiness when required.
- nginx adds HSTS, content type, frame, referrer, and permissions security headers.
- CI runs backend tests, frontend production build, `npm audit`, `pip-audit`, Docker Compose validation, Docker build, and Trivy image scanning.
- Encrypted backup scripts protect database and upload backups with AES-256 and PBKDF2.

Evidence:

- `backend/main.py`
- `.github/workflows/deploy.yml`
- `ops/backups/backup_encrypted.sh`
- `ops/backups/restore_encrypted.sh`

## Required Controls Not Yet Proven

### Encryption At Rest

Required evidence:

- Production host disk encryption or equivalent encrypted block volume.
- Postgres data volume encryption.
- Uploads volume encryption.
- Encrypted backups.
- Key ownership and rotation policy.

Current repository evidence is insufficient. `docker-compose.yml` uses local Docker volumes and does not prove encryption.

### Encryption In Transit

Required evidence:

- TLS certificate for `nephroai.ec` and `app.nephroai.ec`.
- HTTP to HTTPS redirect.
- HSTS header.
- Certificate renewal automation.
- LiveKit TLS/WSS configuration for production.

Current repository evidence shows a public HTTPS health check but nginx inside compose listens on port 80. TLS may be handled outside this compose file; capture that config as evidence.

### Remaining Audit Logging Coverage

Minimum remaining events to log:

- Login success/failure and logout if implemented.
- Password reset requested and completed.
- Export/delete/account deletion events.
- Admin or SSH production access, if applicable.

Recommended fields:

- `id`, `created_at`, `actor_user_id`, `actor_role`, `action`, `resource_type`, `resource_id`, `patient_id`, `doctor_id`, `ip_address`, `user_agent`, `request_id`, `status`, `metadata`.

### Vulnerability Management

Current CI has frontend audit only. Add:

- Python dependency scan: `pip-audit` or Safety.
- Container scan: Trivy or Docker Scout.
- Monthly vulnerability review.
- Patch SLA: critical 7 days, high 14 days, medium 30 days unless risk accepted.

### Access Management

Define and evidence:

- Who has GitHub admin access.
- Who can push to `main`.
- Branch protection for `main`.
- Who has SSH access to production.
- Who can read `.env` and database backups.
- Quarterly access review.
- Offboarding checklist.

### Data Retention

Define:

- Uploaded PDF retention period.
- Extracted lab result retention period.
- Consultation message/call metadata retention period.
- Backup retention period.
- Account deletion and export procedure.

## Customer-Facing Security Summary

NephroAI uses authenticated access, hashed passwords, JWT sessions, patient-controlled doctor grants, production CI/CD gates, and health checks. The app is designed so doctors can only access patient information after explicit patient authorization. NephroAI is preparing formal SOC 2 controls around encryption evidence, audit logging, monitoring, incident response, vulnerability management, and access reviews.

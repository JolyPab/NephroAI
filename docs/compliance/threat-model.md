# Threat Model

Date: 2026-05-19  
Method: STRIDE-lite focused on NephroAI production SaaS

## Assets

- Patient account data.
- Patient lab PDFs and extracted laboratory results.
- Doctor notes and consultation messages.
- Doctor-patient access grants.
- JWT secrets, OpenAI API keys, SMTP credentials, LiveKit credentials.
- Production database and uploads volume.
- CI/CD deployment credentials.

## Entry Points

- Public web frontend.
- `/api/auth/*` endpoints.
- PDF upload/import endpoints.
- Patient and doctor API endpoints.
- Consultation WebSocket endpoint.
- LiveKit proxy.
- GitHub Actions deploy path over SCP/SSH.
- SMTP and OpenAI outbound integrations.

## Threats and Controls

| Threat | Risk | Existing controls | Gaps / next controls |
| --- | --- | --- | --- |
| Credential stuffing against login | Account takeover | Password hashing; email verification | Add login rate limiting, IP/device anomaly alerts, optional MFA for doctors/admins. |
| Password reset abuse | Account takeover or email abuse | Code TTL, cooldown, max attempts, max sends, reset token purpose | Add audit logging and alert spikes. |
| JWT secret exposure | Full account compromise | Production requires JWT secret; GitHub secrets used for deploy | Rotate secrets, document owners, scan git history. |
| Doctor reads patient data without authorization | Confidentiality breach | `DoctorGrant`; `_ensure_doctor_access()`; consultation participant checks | Add audit logging and tests for every doctor route. |
| Patient grant remains after relationship ends | Excessive access | Revocation endpoint exists | Add access review UX, grant expiration option, audit logs. |
| Uploaded PDF contains malware or active content | Backend/file handling risk | PDF parsing libraries process uploaded PDFs | Add malware scanning, file type validation evidence, parser sandboxing policy. |
| PHI sent to AI vendor without adequate agreement | Vendor/compliance risk | OpenAI key isolated in env | Document vendor terms, data retention, consent, minimum data sent. |
| Database or upload volume copied from host | Data breach | Docker volumes on server, Application-level encryption (Fernet) for uploads, encrypted backups | Enforce least-privilege host access. |
| Internal traffic intercepted inside Docker network | Data breach | Strict Docker network isolation from public internet | Document accepted risk for plaintext communication inside internal Docker network. |
| HTTP traffic intercepted | Data breach | Public endpoint uses HTTPS health check | Prove TLS termination, redirect, HSTS, WSS for calls. |
| Broken deploy exposes bad build | Availability/integrity | CI tests, frontend build, Docker checks, health checks before/after deploy | Add branch protection and rollback runbook. |
| Dependency vulnerability exploited | RCE/data breach | Frontend `npm audit` in CI | Add Python and container vulnerability scans. |
| Insufficient monitoring delays incident response | Longer breach/outage | Docker logs and health endpoint | Add centralized logs, error tracking, uptime alerts, incident runbook. |
| Production SSH key abused | Full system compromise | GitHub secrets for SSH deploy | Restrict SSH user, key rotation, server hardening, audit logs, least privilege. |

## Abuse Cases

### A doctor tries to enumerate patients

Expected behavior:

- Doctor endpoints return only patients with active grants.
- Direct patient IDs without grant return 403.

Evidence:

- `backend/tests/test_v2_doctor_endpoints.py`
- `backend/tests/test_consultations.py`

Additional control:

- Audit failed and successful doctor access attempts.

### A patient revokes access while a consultation exists

Expected behavior:

- Grant `revoked_at` prevents further participant access.
- Existing thread should not allow new messages/calls after revoke.

Additional control:

- Add regression test for message/call after revoke.
- Audit revoke event and notify doctor.

### An attacker gets a production database backup

Expected behavior:

- Backup should be encrypted and access-controlled.

Current status:

- No backup encryption evidence found.

Required control:

- Encrypted backups with tested restore and restricted access.

## Risk Register

| ID | Risk | Severity | Owner | Target |
| --- | --- | --- | --- | --- |
| TM-001 | No proven encryption at rest for DB/uploads/backups | Resolved | Engineering | - |
| TM-002 | No application audit log for medical data access | Resolved | Engineering | - |
| TM-003 | No centralized alerting/observability | High | Engineering | 7 days |
| TM-004 | Production compose has default DB credentials | High | Engineering | Immediate |
| TM-005 | TLS/HSTS evidence not captured in repo | Medium | Engineering/Ops | 7 days |
| TM-006 | Python/container vulnerability scanning absent | Medium | Engineering | 14 days |
| TM-007 | Vendor management for OpenAI/SMTP/LiveKit not documented | Medium | Founder/Ops | 14 days |

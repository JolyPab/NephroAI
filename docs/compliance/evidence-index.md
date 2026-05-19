# Evidence Index

Date: 2026-05-19

Use this index to collect screenshots, command output, configuration exports, and policy documents for SOC 2 readiness or customer security review.

## Repository Evidence

| Evidence | Location | Status |
| --- | --- | --- |
| CI/CD workflow | `.github/workflows/deploy.yml` | Available |
| Docker production topology | `docker-compose.yml` | Available |
| nginx routing | `nginx.conf` | Available |
| Auth implementation | `backend/auth.py`, `backend/auth_routes.py` | Available |
| Database schema | `backend/database.py` | Available |
| Health endpoint | `backend/main.py` | Available |
| Production preflight | `docs/compliance/production-preflight.md` | Available |
| Backup and restore runbook | `docs/compliance/backup-and-restore.md` | Available |
| Encrypted backup scripts | `ops/backups/backup_encrypted.sh`, `ops/backups/restore_encrypted.sh` | Available |
| Healthcheck script | `ops/monitoring/healthcheck.sh` | Available |
| Evidence collector | `ops/evidence/collect_evidence.sh` | Available |
| Security policy baseline | `docs/compliance/policies.md` | Available |
| Investor security brief | `docs/compliance/investor-security-brief.md` | Available |
| Doctor access tests | `backend/tests/test_v2_doctor_endpoints.py` | Available |
| Consultation access tests | `backend/tests/test_consultations.py` | Available |
| Password reset tests | `backend/tests/test_auth_password_reset.py` | Available |

## Evidence To Capture

### GitHub

- Repository visibility: private.
- Branch protection for `main`.
- Required CI checks.
- Recent successful deploy workflow.
- GitHub Actions secrets list, names only.
- Dependency alerts / Dependabot status.
- Access list for collaborators/admins.

### Production Server

- Current deployed commit SHA.
- `docker compose ps`.
- `docker compose config` with secrets redacted.
- Host firewall rules.
- SSH users and authorized keys, redacted.
- Disk encryption or encrypted volume evidence.
- Backup job configuration and latest successful backup.
- Latest restore test result.

Repository-provided collector:

```bash
cd /root/medic
sh ops/evidence/collect_evidence.sh
```

### TLS and Domains

- TLS certificate details for `nephroai.ec`.
- TLS certificate details for `app.nephroai.ec`.
- HTTP to HTTPS redirect evidence.
- HSTS response header evidence.
- Certificate renewal automation.
- LiveKit WSS/TLS evidence if production calls use public LiveKit.

Useful commands:

```bash
curl -I https://app.nephroai.ec
curl -I http://app.nephroai.ec
curl -I https://nephroai.ec
curl -fsS https://app.nephroai.ec/api/health
curl -fsS https://app.nephroai.ec/api/health/ready
```

### Monitoring

- Uptime monitor configuration.
- Alert destinations and escalation contacts.
- Error tracking dashboard.
- Log retention settings.
- Incident response test or tabletop evidence.

### Vendors

- OpenAI data processing/security terms.
- SMTP/Resend security terms.
- LiveKit deployment/security terms.
- GitHub security terms.
- Hosting provider security details.

### Policies

- Access control policy.
- Change management policy.
- Incident response policy.
- Vulnerability management policy.
- Backup and restore policy.
- Data retention/deletion policy.
- Vendor management policy.
- Privacy policy and terms of service.

## Evidence Naming Convention

Store collected evidence outside git if it contains secrets, user data, infrastructure details, or screenshots with sensitive values.

Recommended naming:

```text
YYYY-MM-DD_control-area_short-description.ext
2026-05-19_cicd_github-actions-successful-deploy.png
2026-05-19_tls_app-nephroai-curl-headers.txt
2026-05-19_access_github-collaborators-redacted.png
```

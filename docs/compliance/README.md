# NephroAI Compliance Binder

Date: 2026-05-19  
Scope: NephroAI production SaaS at `https://app.nephroai.ec`, backend API, frontend web app, Docker deployment, CI/CD, and patient-doctor data workflows.

This folder is a working SOC 2 readiness binder. It is not a SOC 2 report and does not replace an auditor, but it gives NephroAI a concrete evidence map, control inventory, and remediation plan.

## Documents

- [SOC 2 readiness checklist](soc2-readiness.md)
- [Architecture document](architecture.md)
- [Security controls](security-controls.md)
- [Threat model](threat-model.md)
- [CI/CD and change management](ci-cd-and-change-management.md)
- [Observability and incident response](observability-and-incident-response.md)
- [Evidence index](evidence-index.md)
- [Production preflight](production-preflight.md)
- [Backup and restore](backup-and-restore.md)
- [Security policies](policies.md)
- [Investor security brief](investor-security-brief.md)

## Executive Status

NephroAI has several SOC 2-relevant foundations in place:

- Authenticated API with JWT access tokens and password hashing.
- Patient-owned doctor grants for clinical data access.
- GitHub Actions workflow with backend tests, frontend build, dependency audit, Docker validation, deploy gating, and health checks.
- Docker Compose production topology with API, worker, Postgres, Redis, LiveKit, and nginx.
- Production health endpoint at `/api/health`.
- Production FastAPI docs disabled when `ENV` or `APP_ENV` is production.

The main blockers before a credible SOC 2 readiness review are:

- Formal encryption-at-rest evidence for database volumes, uploads, backups, and host disks.
- Confirmed TLS/HSTS/redirect evidence for all public endpoints.
- Centralized logs, alerting, uptime monitoring, and incident response runbooks.
- Security policies: access review, vendor management, data retention, backup/restore, vulnerability management, incident response, and change management.
- Audit logging for user/admin access to PHI-like medical data.
- Secrets hygiene: remove production default database credentials from deploy path and document secret rotation.

## Immediate Next Actions

1. Complete the gaps marked `Must fix before SOC 2 readiness review` in [SOC 2 readiness checklist](soc2-readiness.md).
2. Add application audit logging for sensitive access and permission changes.
3. Add external uptime monitoring and alerting for `https://app.nephroai.ec/api/health`.
4. Document encryption-at-rest controls for the production host, Postgres volume, uploaded PDFs, and backups.
5. Create written policies and collect screenshots/config exports as evidence.

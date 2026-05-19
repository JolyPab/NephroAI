# Observability and Incident Response

Date: 2026-05-19

## Current Observability

Implemented:

- `/api/health` returns `{"status": "healthy"}`.
- `/api/health/ready` validates database connectivity and Redis when `REQUIRE_REDIS_HEALTH=true` or production mode is enabled.
- GitHub Actions checks local and public health after deploy.
- Docker logs are available for API and worker containers.
- Python modules use standard `logging` in several services.
- Docker Compose has Postgres health check.

Evidence:

- `backend/main.py`
- `.github/workflows/deploy.yml`
- `docker-compose.yml`

Current limitations:

- No centralized log storage found.
- No uptime monitor config found.
- No alert routing found.
- No error tracking found.
- Health endpoint does not verify database, Redis, OpenAI, SMTP, or worker state.
- No documented incident response process found before this binder.

## Required Monitoring

Minimum monitors:

- Public API health: `https://app.nephroai.ec/api/health` every 1 minute.
- Frontend availability: `https://app.nephroai.ec` every 1 minute.
- Landing availability: `https://nephroai.ec` every 5 minutes.
- TLS certificate expiry for both domains.
- Docker container status for api, worker, db, redis, nginx, livekit.
- Disk utilization on production server.
- Postgres availability and storage.
- Redis availability.
- Background worker failures.
- 5xx API error rate.
- Login/password reset error spikes.
- OpenAI and SMTP integration failures.

Recommended tools:

- UptimeRobot, Better Stack, Grafana Cloud, Sentry, or equivalent.
- Docker logs shipped to centralized storage.
- Sentry for frontend/backend exceptions.

Repository-provided check:

```bash
sh ops/monitoring/healthcheck.sh
```

Recommended cron until an external monitor is configured:

```cron
*/5 * * * * cd /root/medic && APP_URL=https://app.nephroai.ec LANDING_URL=https://nephroai.ec sh ops/monitoring/healthcheck.sh >> /root/medic/healthcheck.log 2>&1
```

## Alert Severity

| Severity | Examples | Response target |
| --- | --- | --- |
| SEV1 | App down, data breach suspected, database unavailable, deploy broke production | Start response within 15 minutes |
| SEV2 | PDF extraction down, doctor consultations down, high 5xx rate | Start response within 1 hour |
| SEV3 | Non-critical UI issue, degraded external provider, isolated user report | Triage within 1 business day |

## Incident Response Runbook

1. Detect

- Alert from monitoring, user report, GitHub Actions failure, or logs.
- Create an incident note with timestamp, reporter, affected service, and severity.

2. Triage

- Check public health:

```bash
curl -fsS https://app.nephroai.ec/api/health
curl -fsS https://app.nephroai.ec/api/health/ready
```

- Check server containers:

```bash
cd /root/medic
docker compose ps
docker logs medic-api-1 --tail=200
docker logs medic-worker-1 --tail=200
```

- Check latest deploy SHA and GitHub Actions run.

3. Contain

- If caused by deploy, rollback using the CI/CD rollback runbook.
- If secret exposure is suspected, rotate affected secrets immediately.
- If unauthorized data access is suspected, disable affected user/doctor access and preserve logs.

4. Eradicate and Recover

- Patch the root cause.
- Run tests and deploy.
- Confirm health checks.
- Validate affected workflows manually.

5. Communicate

- Internal incident owner posts status updates.
- For customer-impacting incidents, prepare a Spanish-facing user update if needed.
- For security incidents involving personal/medical data, consult legal/regulatory requirements.

6. Post-Incident Review

Record:

- Timeline.
- Root cause.
- User/data impact.
- Detection gap.
- Corrective actions.
- Preventive actions.
- Owner and due date for each action.

## Logging Requirements

Application logs should include:

- Timestamp.
- Request ID.
- Endpoint/action.
- Actor user ID when authenticated.
- Resource ID.
- Status code/result.
- Exception class and safe error message.

Do not log:

- Passwords.
- JWTs.
- OTP codes.
- OpenAI API keys.
- SMTP credentials.
- Full lab PDFs.
- Full medical context unless explicitly approved for secure audit storage.

## Readiness Gaps

- Add centralized log retention for at least 90 days.
- Add uptime and error alerts.
- Add request IDs.
- Add structured audit logs for sensitive data access.
- Add readiness endpoint that verifies DB/Redis connectivity.
- Document backup restore test results.

# Production Preflight

Date: 2026-05-19

Run this before pushing SOC 2/security-control changes to `main`.

## Required Server Env

On the production server, confirm `/root/medic/.env` contains non-default values:

```bash
cd /root/medic
grep -E '^(POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|JWT_SECRET|ENV|CORS_ORIGINS|REDIS_URL)=' .env
```

Required:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `JWT_SECRET`
- `ENV=production`
- `CORS_ORIGINS=https://app.nephroai.ec`
- `BACKUP_ENCRYPTION_KEY`

Recommended:

- `REQUIRE_REDIS_HEALTH=true`
- `SMTP_REQUIRE_DELIVERY=true`
- production `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`

## Local Checks

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
backend/.venv/Scripts/pip-audit.exe -r backend/requirements.txt --progress-spinner off --timeout 15
$env:POSTGRES_USER='medic_ci'; $env:POSTGRES_PASSWORD='medic_ci_password'; $env:POSTGRES_DB='medic_ci'; docker compose config --quiet
```

If Docker daemon is running:

```bash
docker run --rm -v ${PWD}/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t
```

## After Deploy

```bash
curl -fsS https://app.nephroai.ec/api/health
curl -fsS https://app.nephroai.ec/api/health/ready
curl -I https://app.nephroai.ec
curl -I https://nephroai.ec
sh ops/monitoring/healthcheck.sh
sh ops/evidence/collect_evidence.sh
```

Expected:

- `/api/health` returns `{"status":"healthy"}`.
- `/api/health/ready` returns `status=ready`.
- Headers include `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`.

## Evidence To Save

- Successful GitHub Actions run.
- Public health and readiness command output.
- Header output from both domains.
- Server `docker compose ps`.
- Confirmation that `/root/medic/.env` uses non-default database credentials, with secrets redacted.

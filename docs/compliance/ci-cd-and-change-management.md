# CI/CD and Change Management

Date: 2026-05-19

## Current CI/CD Flow

NephroAI deploys from `main` using GitHub Actions.

Workflow file:

- `.github/workflows/deploy.yml`

Triggers:

- Pull requests targeting `main`.
- Pushes to `main`.

Jobs:

- `backend-tests`: installs Python 3.11 dependencies and runs `python -m pytest backend/tests -v`.
- `frontend-build`: installs Node 20 dependencies, runs `npm run build`, then `npm audit --omit=dev --audit-level=moderate`.
- `docker-check`: validates Docker Compose config and builds backend image.
- `deploy`: only on push to `main`, after all prior jobs pass.

Deploy mechanism:

1. GitHub Actions downloads frontend artifact.
2. `appleboy/scp-action` copies app files to production server.
3. `appleboy/ssh-action` runs Docker Compose deployment on `~/medic`.
4. Deployment checks JWT secret visibility in the API container.
5. Deployment checks local health at `http://localhost/api/health`.
6. Workflow checks public health at `https://app.nephroai.ec/api/health`.

## Existing Evidence

- `.github/workflows/deploy.yml`
- GitHub Actions run history for `main`.
- Public health check result.
- Docker Compose config.
- Backend test output.
- Frontend build output.
- `npm audit` output.

## Required Change Management Policy

All production changes must follow this policy:

- Changes are committed to git with descriptive commit messages (`fix:`, `feat:`, `refactor:`).
- Changes to `main` must pass CI before deployment.
- Security-sensitive changes require explicit review by the repository owner or designated reviewer.
- Failed deploys must be rolled back or fixed immediately.
- Incidents caused by changes require a post-incident note with cause, impact, correction, and prevention.

## Required GitHub Settings Evidence

Capture screenshots or exported settings for:

- Repository is private.
- `main` branch protection is enabled.
- Required status checks include backend tests, frontend build, and Docker check.
- Direct pushes to `main` are restricted or owner-approved.
- GitHub Actions secrets are restricted to required deploy secrets.
- Dependabot or equivalent dependency alerting is enabled.

## Recommended CI Improvements

Add these checks before SOC 2 readiness review:

```yaml
- name: Python dependency audit
  working-directory: backend
  run: |
    python -m pip install pip-audit
    pip-audit -r requirements.txt
```

Add a container scan:

```yaml
- name: Scan backend image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: nephroai-api-ci
    severity: CRITICAL,HIGH
    exit-code: "1"
```

Add deployment evidence retention:

- Save test/build/deploy logs in GitHub Actions for at least 90 days.
- Tag production releases or record deployed commit SHA.

## Rollback Runbook

1. Identify last known good commit from GitHub Actions history.
2. Revert the faulty commit or redeploy the previous commit.
3. Run backend tests, frontend build, and Docker check.
4. Push to `main` to trigger deploy.
5. Confirm `https://app.nephroai.ec/api/health`.
6. Check API and worker logs:

```bash
cd /root/medic
docker compose ps
docker logs medic-api-1 --tail=200
docker logs medic-worker-1 --tail=200
```

7. Record incident/change note with timeline and impact.

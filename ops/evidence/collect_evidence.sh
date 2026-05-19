#!/usr/bin/env sh
set -eu

# Collect non-secret SOC 2 readiness evidence on the production server.
# Run from /root/medic after deploy.

APP_URL="${APP_URL:-https://app.nephroai.ec}"
LANDING_URL="${LANDING_URL:-https://nephroai.ec}"
OUT_ROOT="${EVIDENCE_DIR:-/root/medic/evidence}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$OUT_ROOT/$STAMP"

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_ROOT" "$OUT_DIR"

run_capture() {
  name="$1"
  shift
  {
    echo "$ $*"
    "$@"
  } > "$OUT_DIR/$name.txt" 2>&1 || {
    status="$?"
    echo "command failed with status $status" >> "$OUT_DIR/$name.txt"
    return 0
  }
}

run_capture "git-status" git status --short
run_capture "git-revision" git rev-parse HEAD
run_capture "docker-compose-ps" docker compose ps
run_capture "api-health" curl -fsS "$APP_URL/api/health"
run_capture "api-readiness" curl -fsS "$APP_URL/api/health/ready"
run_capture "app-headers" curl -fsSI "$APP_URL"
run_capture "landing-headers" curl -fsSI "$LANDING_URL"
run_capture "compose-config-redacted" sh -c "docker compose config | sed -E 's/(PASSWORD|SECRET|KEY|TOKEN): .*/\\1: REDACTED/g'"

if [ -d "/root/medic/backups" ]; then
  run_capture "backup-inventory" sh -c "find /root/medic/backups -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %f\n' | sort | tail -20"
fi

cat > "$OUT_DIR/README.txt" <<EOF
NephroAI SOC 2 readiness evidence
Collected: $STAMP
App URL: $APP_URL
Landing URL: $LANDING_URL

Review files before sharing externally. Do not add secrets or patient data.
EOF

echo "Evidence collected in $OUT_DIR"

#!/usr/bin/env sh
set -eu

APP_URL="${APP_URL:-https://app.nephroai.ec}"
LANDING_URL="${LANDING_URL:-https://nephroai.ec}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-10}"

check_url() {
  label="$1"
  url="$2"
  if curl -fsS --max-time "$TIMEOUT_SECONDS" "$url" >/dev/null; then
    echo "ok $label $url"
  else
    echo "fail $label $url" >&2
    return 1
  fi
}

check_header() {
  label="$1"
  url="$2"
  header="$3"
  if curl -fsSI --max-time "$TIMEOUT_SECONDS" "$url" | grep -iq "^$header:"; then
    echo "ok $label header $header"
  else
    echo "fail $label missing header $header" >&2
    return 1
  fi
}

check_url "app" "$APP_URL"
check_url "landing" "$LANDING_URL"
check_url "api-health" "$APP_URL/api/health"
check_url "api-ready" "$APP_URL/api/health/ready"

check_header "app" "$APP_URL" "Strict-Transport-Security"
check_header "app" "$APP_URL" "X-Content-Type-Options"
check_header "app" "$APP_URL" "X-Frame-Options"
check_header "landing" "$LANDING_URL" "Strict-Transport-Security"

echo "NephroAI healthcheck complete."

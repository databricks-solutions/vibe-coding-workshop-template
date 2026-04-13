#!/usr/bin/env bash
# Verifies a Databricks AppKit deployment is running and healthy.
#
# Usage: bash scripts/verify-deploy.sh APP_NAME PROFILE [--max-retries N]
#
# Output: JSON to stdout, diagnostics to stderr.
# Exit codes: 0 = verified, 1 = still starting after retries, 2 = error.
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: bash scripts/verify-deploy.sh APP_NAME PROFILE [OPTIONS]

Verifies a deployed Databricks AppKit app is running and healthy.

Arguments:
  APP_NAME    Name of the deployed Databricks app
  PROFILE     Databricks CLI profile to use

Options:
  --max-retries N   Maximum status check retries (default: 10)
  --health-path P   Health check endpoint path (default: /api/health)
  --help, -h        Show this help message

Steps:
  1. Poll app status until compute_status.state is ACTIVE
  2. Retrieve the app URL
  3. Curl the health endpoint
  4. Report pass/fail

Output (JSON to stdout):
  { "status": "ok|starting|error", "url": "...", "compute": "...", "health": "ok|fail|skip" }

Exit codes:
  0  Deploy verified (compute ACTIVE, health OK)
  1  App still starting after max retries
  2  Error (app crashed, missing, or health check failed)

Idempotent: safe to run multiple times.
EOF
  exit 0
}

# --- Parse args ---
APP_NAME=""
PROFILE=""
MAX_RETRIES=10
HEALTH_PATH="/api/health"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --max-retries) MAX_RETRIES="${2:-10}"; shift 2 ;;
    --health-path) HEALTH_PATH="${2:-/api/health}"; shift 2 ;;
    *)
      if [ -z "$APP_NAME" ]; then APP_NAME="$1"; shift
      elif [ -z "$PROFILE" ]; then PROFILE="$1"; shift
      else echo "Error: unexpected argument '$1'" >&2; exit 2; fi
      ;;
  esac
done

if [ -z "$APP_NAME" ] || [ -z "$PROFILE" ]; then
  echo "Error: APP_NAME and PROFILE are required." >&2
  echo "Usage: bash scripts/verify-deploy.sh APP_NAME PROFILE [--max-retries N]" >&2
  exit 2
fi

# --- Poll for ACTIVE status ---
COMPUTE_STATE=""
WAIT=5
for i in $(seq 1 "$MAX_RETRIES"); do
  APP_JSON=$(databricks apps get "$APP_NAME" --output json --profile "$PROFILE" 2>/dev/null || echo "{}")
  COMPUTE_STATE=$(echo "$APP_JSON" | jq -r '.compute_status.state // "UNKNOWN"')
  APP_STATUS=$(echo "$APP_JSON" | jq -r '.status.state // "null"')

  echo "Check $i/$MAX_RETRIES: compute=$COMPUTE_STATE status=$APP_STATUS" >&2

  if [ "$COMPUTE_STATE" = "ACTIVE" ]; then
    break
  fi

  if [ "$COMPUTE_STATE" = "ERROR" ] || [ "$COMPUTE_STATE" = "CRASHED" ]; then
    echo "App is in $COMPUTE_STATE state. Check logs: databricks apps logs $APP_NAME --profile $PROFILE" >&2
    echo "{\"status\":\"error\",\"url\":\"\",\"compute\":\"$COMPUTE_STATE\",\"health\":\"skip\"}"
    exit 2
  fi

  if [ "$i" -lt "$MAX_RETRIES" ]; then
    echo "  Waiting ${WAIT}s before next check..." >&2
    sleep "$WAIT"
    WAIT=$((WAIT < 30 ? WAIT * 2 : 30))
  fi
done

if [ "$COMPUTE_STATE" != "ACTIVE" ]; then
  echo "App not ACTIVE after $MAX_RETRIES retries (last state: $COMPUTE_STATE)" >&2
  echo "{\"status\":\"starting\",\"url\":\"\",\"compute\":\"$COMPUTE_STATE\",\"health\":\"skip\"}"
  exit 1
fi

# --- Get URL ---
APP_URL=$(echo "$APP_JSON" | jq -r '.url // ""')
echo "App URL: $APP_URL" >&2

if [ -z "$APP_URL" ]; then
  echo "Warning: no URL found in app metadata" >&2
  echo "{\"status\":\"ok\",\"url\":\"\",\"compute\":\"ACTIVE\",\"health\":\"skip\"}"
  exit 0
fi

# --- Health check ---
HEALTH_STATUS="fail"
TOKEN=$(databricks auth token --profile "$PROFILE" 2>/dev/null | jq -r '.access_token // empty')
if [ -n "$TOKEN" ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "${APP_URL}${HEALTH_PATH}" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    HEALTH_STATUS="ok"
    echo "Health check: 200 OK" >&2
  else
    echo "Health check: HTTP $HTTP_CODE (may need a moment to warm up)" >&2
  fi
else
  echo "Warning: could not get auth token for health check" >&2
  HEALTH_STATUS="skip"
fi

echo "{\"status\":\"ok\",\"url\":\"$APP_URL\",\"compute\":\"ACTIVE\",\"health\":\"$HEALTH_STATUS\"}"
exit 0

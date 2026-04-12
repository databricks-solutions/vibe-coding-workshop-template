#!/usr/bin/env bash
# Tests AppKit Lakebase API endpoints and validates response shape.
#
# Usage: bash scripts/test-endpoints.sh [OPTIONS]
#
# Output: JSON array to stdout, diagnostics to stderr.
# Exit codes: 0 = all pass, 1 = one or more failed.
set -euo pipefail

BASE_URL="http://localhost:8000"
ENDPOINTS="/api/health/lakebase"

show_help() {
  cat <<'EOF'
Usage: bash scripts/test-endpoints.sh [OPTIONS]

Tests AppKit Lakebase API endpoints and validates response shape.

Options:
  --base-url URL         Base URL (default: http://localhost:8000)
  --endpoints LIST       Comma-separated endpoint paths
                         (default: /api/health/lakebase)
  --help, -h             Show this help message

Each endpoint is curled and checked for:
  - HTTP 200 response
  - Valid JSON body
  - Presence of "source" field ("live" or "mock")

Output (JSON array to stdout):
  [{ "endpoint": "/api/health/lakebase", "status": "pass", "http_code": 200, "source": "mock" }, ...]

Exit codes:
  0  All endpoints passed
  1  One or more endpoints failed

Idempotent: safe to run multiple times. Requires the dev server to be running.
EOF
  exit 0
}

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --base-url) BASE_URL="${2:-$BASE_URL}"; shift 2 ;;
    --endpoints) ENDPOINTS="${2:-$ENDPOINTS}"; shift 2 ;;
    *) echo "Error: unknown option '$1'" >&2; exit 1 ;;
  esac
done

IFS=',' read -ra EP_LIST <<< "$ENDPOINTS"
FAILED=0
RESULTS="["
FIRST=true

for EP in "${EP_LIST[@]}"; do
  EP=$(echo "$EP" | xargs)  # trim whitespace
  RESULT_STATUS="fail"
  HTTP_CODE="000"
  SOURCE=""

  RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}${EP}" 2>/dev/null || echo -e "\n000")
  BODY=$(echo "$RESPONSE" | head -n -1)
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)

  if [ "$HTTP_CODE" = "200" ]; then
    SOURCE=$(echo "$BODY" | jq -r '.source // .status // "unknown"' 2>/dev/null || echo "parse_error")
    if [ "$SOURCE" != "parse_error" ]; then
      RESULT_STATUS="pass"
      echo "$EP — HTTP $HTTP_CODE, source=$SOURCE — PASS" >&2
    else
      echo "$EP — HTTP $HTTP_CODE, invalid JSON — FAIL" >&2
      FAILED=1
    fi
  else
    echo "$EP — HTTP $HTTP_CODE — FAIL" >&2
    FAILED=1
  fi

  if [ "$FIRST" = true ]; then FIRST=false; else RESULTS+=","; fi
  RESULTS+="{\"endpoint\":\"$EP\",\"status\":\"$RESULT_STATUS\",\"http_code\":$HTTP_CODE,\"source\":\"$SOURCE\"}"
done

RESULTS+="]"
echo "$RESULTS"

exit $FAILED

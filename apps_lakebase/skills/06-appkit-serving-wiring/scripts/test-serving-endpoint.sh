#!/usr/bin/env bash
# Tests AppKit Serving plugin endpoints and validates response shape.
#
# SCOPE: IDE/local-dev convenience (NON-CANONICAL). Defaults to a local dev server
#   at http://localhost:8000 and uses raw-Bearer curl, neither of which works on Genie
#   Code (no local dev server; the Apps OAuth gate rejects raw Bearer). The canonical
#   cross-client verification is the deployed-app path: browser chat test +
#   `databricks apps logs <name>`, or the 3-hop OAuth `requests.Session()` test in
#   03-appkit-deploy. `bash -n` syntax-checks fine offline.
#
# Usage: bash scripts/test-serving-endpoint.sh [OPTIONS]
#
# Output: JSON array to stdout, diagnostics to stderr.
# Exit codes: 0 = all pass, 1 = one or more failed.
set -euo pipefail

BASE_URL="http://localhost:8000"
ALIAS="default"
MODE="appkit"
ENDPOINT_NAME=""
PROFILE=""
TOKEN=""
MESSAGE="Hello, what can you help with?"

show_help() {
  cat <<'EOF'
Usage: bash scripts/test-serving-endpoint.sh [OPTIONS]

Tests AppKit Serving plugin HTTP endpoints or raw Databricks serving endpoints.

Options:
  --base-url URL         Base URL for AppKit app (default: http://localhost:8000)
  --alias ALIAS          Serving endpoint alias (default: default)
  --message TEXT         Test message to send (default: "Hello, what can you help with?")
  --token TOKEN          Bearer token for deployed app auth (omit for localhost)
  --endpoint-name NAME   Also test the raw Databricks serving endpoint via CLI
  --profile PROFILE      Databricks CLI profile (required with --endpoint-name)
  --help, -h             Show this help message

Tests performed:
  1. POST /api/serving/:alias/invoke — non-streaming invocation
  2. (Optional) databricks serving-endpoints get <name> — endpoint status check

Each endpoint is tested for:
  - HTTP 200 response
  - Valid JSON body
  - Non-empty response content

Output (JSON array to stdout):
  [{ "test": "invoke", "status": "pass", "http_code": 200, "has_content": true }, ...]

Exit codes:
  0  All tests passed
  1  One or more tests failed

Idempotent: safe to run multiple times. Requires the app to be running.
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --base-url) BASE_URL="${2:-$BASE_URL}"; shift 2 ;;
    --alias) ALIAS="${2:-$ALIAS}"; shift 2 ;;
    --message) MESSAGE="${2:-$MESSAGE}"; shift 2 ;;
    --token) TOKEN="${2:-}"; shift 2 ;;
    --endpoint-name) ENDPOINT_NAME="${2:-}"; MODE="both"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    *) echo "Error: unknown option '$1'" >&2; exit 1 ;;
  esac
done

FAILED=0
RESULTS="["
FIRST=true

add_result() {
  local test_name="$1" status="$2" http_code="$3" has_content="$4"
  if [ "$FIRST" = true ]; then FIRST=false; else RESULTS+=","; fi
  RESULTS+="{\"test\":\"$test_name\",\"status\":\"$status\",\"http_code\":$http_code,\"has_content\":$has_content}"
}

# --- Test 1: AppKit invoke endpoint ---
INVOKE_PATH="/api/serving/${ALIAS}/invoke"
if [ "$ALIAS" = "default" ]; then
  INVOKE_PATH="/api/serving/invoke"
fi

BODY="{\"messages\":[{\"role\":\"user\",\"content\":\"${MESSAGE}\"}]}"

CURL_ARGS=(-s -w "\n%{http_code}" -X POST "${BASE_URL}${INVOKE_PATH}" -H "Content-Type: application/json" -d "$BODY")
if [ -n "$TOKEN" ]; then
  CURL_ARGS+=(-H "Authorization: Bearer $TOKEN")
fi

echo "Testing POST ${BASE_URL}${INVOKE_PATH} ..." >&2
RESPONSE=$(curl "${CURL_ARGS[@]}" 2>/dev/null || echo -e "\n000")

RESP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  HAS_CONTENT=$(echo "$RESP_BODY" | jq -e 'length > 0' 2>/dev/null && echo "true" || echo "false")
  if [ "$HAS_CONTENT" = "true" ]; then
    echo "${INVOKE_PATH} — HTTP $HTTP_CODE — PASS" >&2
    add_result "invoke" "pass" "$HTTP_CODE" "true"
  else
    echo "${INVOKE_PATH} — HTTP $HTTP_CODE, empty body — FAIL" >&2
    add_result "invoke" "fail" "$HTTP_CODE" "false"
    FAILED=1
  fi
else
  echo "${INVOKE_PATH} — HTTP $HTTP_CODE — FAIL" >&2
  add_result "invoke" "fail" "$HTTP_CODE" "false"
  FAILED=1
fi

# --- Test 2 (optional): Raw Databricks endpoint status ---
if [ -n "$ENDPOINT_NAME" ]; then
  echo "Testing databricks serving-endpoints get ${ENDPOINT_NAME} ..." >&2
  PROFILE_FLAG=""
  if [ -n "$PROFILE" ]; then
    PROFILE_FLAG="--profile $PROFILE"
  fi

  EP_STATUS=$(databricks serving-endpoints get "$ENDPOINT_NAME" $PROFILE_FLAG --output json 2>/dev/null \
    | jq -r '.state.ready // "UNKNOWN"' 2>/dev/null || echo "ERROR")

  if [ "$EP_STATUS" = "READY" ]; then
    echo "Endpoint ${ENDPOINT_NAME} — status: ${EP_STATUS} — PASS" >&2
    add_result "endpoint_status" "pass" "0" "true"
  else
    echo "Endpoint ${ENDPOINT_NAME} — status: ${EP_STATUS} — FAIL (must be READY)" >&2
    add_result "endpoint_status" "fail" "0" "false"
    FAILED=1
  fi
fi

RESULTS+="]"
echo "$RESULTS"

exit $FAILED

#!/usr/bin/env bash
# Tests the 06d AppKit -> Agent App proxy end-to-end with four probes.
#
# Usage: bash scripts/test-agent-app-proxy.sh [OPTIONS]
#
# Output: JSON array to stdout, diagnostics to stderr.
# Exit codes: 0 = all pass, 1 = one or more failed.
#
# Runtime requirements (this script is offline-author-friendly for `bash -n`
# syntax checks but requires the following to actually execute end-to-end):
#   - Both AppKit App and Agent App deployed and RUNNING.
#   - `databricks` CLI authenticated for $PROFILE; `jq` and `curl` on PATH.
#     CLIENT NOTE (Genie Code): there is no $PROFILE — it is pre-authenticated. Drive
#     the script's `databricks`/`curl` calls via runDatabricksCli/executeCode and omit
#     `--profile`. The browser check (SKILL.md Step 6c) is the simplest manual verify.
#   - The AppKit App's service principal must have CAN_USE on the Agent App
#     (resource binding approval granted in the Apps UI).
#   - Probe 4 additionally requires:
#       * `MLFLOW_TRACING_SQL_WAREHOUSE_ID` — SQL warehouse the trace tables
#         are surfaced through (per Skill 04c).
#       * `MLFLOW_TRACING_TABLE` — fully qualified `<catalog>.<schema>.<prefix>`
#         (the UC v4 trace table prefix). Required to convert between the
#         client form (`trace:/<catalog>.<schema>.<prefix>/<bare_id>`) and the
#         Assessments backend form (bare `<bare_id>` for the SQL lookup).
#       * `EXPECTED_USER_EMAIL` — the originating end user's email. Probe 4
#         asserts this equals `assessment.source_id` (NOT the AppKit SP UUID).
#     If any of these are missing OR the API shape required to read back the
#     assessment is unavailable, Probe 4 fails with the explicit reason
#     `trace_assessment_api_contract_missing` so the caller does not get a
#     false pass.
set -euo pipefail

AGENT_APP_NAME=""
APPKIT_APP_NAME=""
PROFILE=""
MESSAGE="Hello, what can you help with?"
STUB_USER_TOKEN="${STUB_USER_TOKEN:-stub-obo-token-for-forwarding-test}"

show_help() {
  cat <<'EOF'
Usage: bash scripts/test-agent-app-proxy.sh [OPTIONS]

Tests the AppKit -> Agent App proxy end-to-end with four identity-aware probes.

Options:
  --agent-app NAME    Agent App name (required unless --agent-url is given)
  --agent-url URL     Agent App URL (overrides --agent-app lookup)
  --appkit-app NAME   AppKit App name (required unless --appkit-url is given)
  --appkit-url URL    AppKit App URL (overrides --appkit-app lookup)
  --profile PROFILE   Databricks CLI profile (required)
  --message TEXT      Test message (default: "Hello, what can you help with?")
  --expected-email E  Expected end-user email for Probe 4 identity assertion
                      (overrides $EXPECTED_USER_EMAIL).
  --help, -h          Show this help

Probes performed:
  1. agent_direct           — Direct Agent App /invocations with SP auth.
                              Proves the agent is up and reachable.
  2. appkit_sp_only         — AppKit /api/chat with SP-only (no OBO header).
                              Proves the app-to-app proxy path works without
                              an end-user token in the chain.
  3. appkit_with_obo        — AppKit /api/chat with a stub
                              x-forwarded-access-token. Proves OBO header
                              propagation reaches the Agent App.
  4. feedback_source_id     — Identity attribution: log a thumbs-up via the
                              feedback path (or read back the assessment for
                              the trace returned by Probe 3) and assert
                              `assessment.source_id == EXPECTED_USER_EMAIL`,
                              NOT the AppKit App service principal UUID. Uses
                              the canonical UC v4 trace ID conversion contract
                              from Skill 04c (Two-Form trace ID). Fails with
                              `trace_assessment_api_contract_missing` if the
                              required env vars or API shape are unavailable
                              — never silently passes.

Output (JSON array to stdout):
  [{"probe":"agent_direct","status":"pass","http_code":200,"has_content":true},
   {"probe":"appkit_sp_only","status":"pass","http_code":200,"has_content":true},
   {"probe":"appkit_with_obo","status":"pass","http_code":200,"has_content":true},
   {"probe":"feedback_source_id","status":"pass","detail":"source_id matches expected user email"}]

Exit codes:
  0  All probes passed
  1  One or more probes failed (including
     `trace_assessment_api_contract_missing`)

Idempotent: safe to run multiple times. Requires both apps to be deployed.
Prereqs: databricks CLI >= 0.295.0, jq, curl. Probe 4 additionally requires
the env vars documented in the script header (MLFLOW_TRACING_SQL_WAREHOUSE_ID,
MLFLOW_TRACING_TABLE, EXPECTED_USER_EMAIL).
EOF
  exit 0
}

AGENT_URL_OVERRIDE=""
APPKIT_URL_OVERRIDE=""
EXPECTED_EMAIL_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --agent-app) AGENT_APP_NAME="${2:-}"; shift 2 ;;
    --agent-url) AGENT_URL_OVERRIDE="${2:-}"; shift 2 ;;
    --appkit-app) APPKIT_APP_NAME="${2:-}"; shift 2 ;;
    --appkit-url) APPKIT_URL_OVERRIDE="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --message) MESSAGE="${2:-$MESSAGE}"; shift 2 ;;
    --expected-email) EXPECTED_EMAIL_OVERRIDE="${2:-}"; shift 2 ;;
    *) echo "Error: unknown option '$1'" >&2; exit 1 ;;
  esac
done

if [ -z "$PROFILE" ]; then
  echo "Error: --profile is required" >&2
  exit 1
fi

if [ -z "$AGENT_URL_OVERRIDE" ] && [ -z "$AGENT_APP_NAME" ]; then
  echo "Error: --agent-app or --agent-url is required" >&2
  exit 1
fi

if [ -z "$APPKIT_URL_OVERRIDE" ] && [ -z "$APPKIT_APP_NAME" ]; then
  echo "Error: --appkit-app or --appkit-url is required" >&2
  exit 1
fi

for cmd in databricks jq curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' is required but not installed" >&2
    exit 1
  fi
done

resolve_app_url() {
  local name="$1"
  databricks apps get "$name" --profile "$PROFILE" --output json 2>/dev/null \
    | jq -r '.url // empty'
}

strip_trailing_slash() { echo "${1%/}"; }

if [ -n "$AGENT_URL_OVERRIDE" ]; then
  AGENT_URL=$(strip_trailing_slash "$AGENT_URL_OVERRIDE")
else
  AGENT_URL=$(resolve_app_url "$AGENT_APP_NAME")
  AGENT_URL=$(strip_trailing_slash "${AGENT_URL:-}")
fi

if [ -n "$APPKIT_URL_OVERRIDE" ]; then
  APPKIT_URL=$(strip_trailing_slash "$APPKIT_URL_OVERRIDE")
else
  APPKIT_URL=$(resolve_app_url "$APPKIT_APP_NAME")
  APPKIT_URL=$(strip_trailing_slash "${APPKIT_URL:-}")
fi

if [ -z "$AGENT_URL" ]; then
  echo "Error: could not resolve Agent App URL" >&2
  exit 1
fi
if [ -z "$APPKIT_URL" ]; then
  echo "Error: could not resolve AppKit App URL" >&2
  exit 1
fi

echo "Agent App URL:  $AGENT_URL" >&2
echo "AppKit App URL: $APPKIT_URL" >&2

TOKEN=$(databricks auth token --profile "$PROFILE" --output json 2>/dev/null | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
  echo "Error: could not obtain access token for profile '$PROFILE'" >&2
  exit 1
fi

# Resolve expected email for Probe 4 (identity attribution check).
EXPECTED_EMAIL="${EXPECTED_EMAIL_OVERRIDE:-${EXPECTED_USER_EMAIL:-}}"
# Probe 3 uses this email as the inbound x-forwarded-email so the AppKit
# proxy can stamp x-app-user-email outbound (Pathway-C identity propagation).
# If unset, Probe 3 still works (proves header propagation) but Probe 4 will
# fail with trace_assessment_api_contract_missing because we can't assert
# "source_id == this email".
PROBE_EMAIL="${EXPECTED_EMAIL:-probe-user@example.com}"

BODY="{\"messages\":[{\"role\":\"user\",\"content\":$(echo -n "$MESSAGE" | jq -Rs .)}]}"

FAILED=0
RESULTS="["
FIRST=true

# Capture trace_id surfaced by Probe 3 (if the agent emits it in the SSE
# `done` event or JSON body). Probe 4 reads back the assessment for this
# trace to assert source_id attribution. The trace id is in the UC v4
# client form: trace:/<catalog>.<schema>.<prefix>/<bare_id>
PROBE3_TRACE_ID=""

add_result() {
  local probe="$1" status="$2" http_code="$3" has_content="$4"
  if [ "$FIRST" = true ]; then FIRST=false; else RESULTS+=","; fi
  RESULTS+="{\"probe\":\"$probe\",\"status\":\"$status\",\"http_code\":$http_code,\"has_content\":$has_content}"
}

add_identity_result() {
  local probe="$1" status="$2" detail="$3"
  if [ "$FIRST" = true ]; then FIRST=false; else RESULTS+=","; fi
  local detail_json
  detail_json=$(echo -n "$detail" | jq -Rs .)
  RESULTS+="{\"probe\":\"$probe\",\"status\":\"$status\",\"detail\":$detail_json}"
}

# Extracts a trace id (UC v4 client form preferred, bare id fallback) from
# either an SSE stream body or a JSON body. Echoes the trace id, or empty.
extract_trace_id() {
  local body="$1"
  local found=""
  # 1. Try SSE event with type=done containing trace_id.
  found=$(printf '%s' "$body" \
    | grep -oE '"trace_id"[[:space:]]*:[[:space:]]*"[^"]+"' \
    | head -1 \
    | sed -E 's/.*"trace_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' \
    || true)
  if [ -n "$found" ]; then
    printf '%s' "$found"
    return 0
  fi
  # 2. Try Responses API trace.id field.
  found=$(printf '%s' "$body" \
    | grep -oE '"trace"[[:space:]]*:[[:space:]]*{[^}]*"id"[[:space:]]*:[[:space:]]*"[^"]+"' \
    | head -1 \
    | sed -E 's/.*"id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' \
    || true)
  printf '%s' "${found:-}"
}

# Converts a trace id from the UC v4 client form
#   trace:/<catalog>.<schema>.<prefix>/<bare_id>
# to the Assessments backend form. Per Skill 04c, modern Databricks runtimes
# accept the URI as-is; older runtimes require the bare id (segment after
# the last '/'). We emit BOTH and let the caller try them in order.
# Echoes "<client_form>\t<bare_id>".
convert_trace_id_to_assessments_forms() {
  local trace_uri="$1"
  local bare_id="$trace_uri"
  case "$trace_uri" in
    trace:/*)
      # Strip trace:/ prefix, then strip the catalog.schema.prefix segment.
      bare_id="${trace_uri##*/}"
      ;;
  esac
  printf '%s\t%s' "$trace_uri" "$bare_id"
}

run_probe() {
  local probe_name="$1" url="$2" extra_header="$3"

  echo "Probe: $probe_name -> POST $url" >&2

  local curl_args=(-s -w "\n__HTTP_CODE__%{http_code}" -X POST "$url"
    -H "Content-Type: application/json"
    -H "Authorization: Bearer $TOKEN"
    --max-time 120
    -d "$BODY")

  if [ -n "$extra_header" ]; then
    curl_args+=(-H "$extra_header")
  fi

  # Probe 3 also forwards x-forwarded-email so the AppKit proxy stamps
  # x-app-user-email outbound (Pathway-C). This lets Probe 4 assert that
  # the resulting assessment.source_id matches the expected email and not
  # the AppKit SP UUID.
  if [ "$probe_name" = "appkit_with_obo" ]; then
    curl_args+=(-H "x-forwarded-email: $PROBE_EMAIL")
  fi

  local response
  response=$(curl "${curl_args[@]}" 2>/dev/null || echo -e "\n__HTTP_CODE__000")
  local http_code
  http_code=$(echo "$response" | grep -o '__HTTP_CODE__[0-9]*$' | sed 's/__HTTP_CODE__//' | tail -1)
  local body
  body=$(echo "$response" | sed 's/__HTTP_CODE__[0-9]*$//')

  if [ -z "$http_code" ]; then http_code="000"; fi

  local has_content="false"
  if [ -n "$body" ]; then
    has_content="true"
  fi

  # Capture trace id from Probe 3 for Probe 4.
  if [ "$probe_name" = "appkit_with_obo" ] && [ -n "$body" ]; then
    PROBE3_TRACE_ID=$(extract_trace_id "$body")
    if [ -n "$PROBE3_TRACE_ID" ]; then
      echo "  -> captured trace_id: $PROBE3_TRACE_ID" >&2
    fi
  fi

  if [ "$http_code" = "200" ] && [ "$has_content" = "true" ]; then
    echo "  -> HTTP $http_code, body present -> PASS" >&2
    add_result "$probe_name" "pass" "$http_code" "$has_content"
  else
    echo "  -> HTTP $http_code, has_content=$has_content -> FAIL" >&2
    if [ -n "$body" ]; then
      echo "  -> body (first 300 bytes): $(echo "$body" | head -c 300)" >&2
    fi
    add_result "$probe_name" "fail" "$http_code" "$has_content"
    FAILED=1
  fi
}

# Probe 4: assert that the MLflow assessment recorded for the Probe 3 trace
# has source_id == EXPECTED_USER_EMAIL (the originating end user), not the
# AppKit App service principal UUID. Uses the canonical UC v4 trace ID
# conversion contract from Skill 04c.
#
# This probe is intentionally strict: if any of the required env vars or
# API shapes are missing, it FAILS with the explicit reason
# `trace_assessment_api_contract_missing`. It MUST NOT silently pass.
run_feedback_source_id_probe() {
  local probe_name="feedback_source_id"
  echo "Probe: $probe_name -> verify assessment.source_id == originating user email" >&2

  # Required env / inputs.
  if [ -z "$EXPECTED_EMAIL" ]; then
    echo "  -> EXPECTED_USER_EMAIL is unset; cannot verify identity attribution -> FAIL" >&2
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: EXPECTED_USER_EMAIL is unset"
    FAILED=1
    return
  fi

  if [ -z "$PROBE3_TRACE_ID" ]; then
    echo "  -> Probe 3 did not surface a trace_id (agent may not emit trace ids per Skill 04c Pattern A/B); cannot read back assessment -> FAIL" >&2
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: Probe 3 did not return a trace_id (agent must implement Skill 04c Pattern A or B)"
    FAILED=1
    return
  fi

  if [ -z "${MLFLOW_TRACING_SQL_WAREHOUSE_ID:-}" ] || [ -z "${MLFLOW_TRACING_TABLE:-}" ]; then
    echo "  -> MLFLOW_TRACING_SQL_WAREHOUSE_ID and/or MLFLOW_TRACING_TABLE unset; cannot read assessments -> FAIL" >&2
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: MLFLOW_TRACING_SQL_WAREHOUSE_ID or MLFLOW_TRACING_TABLE unset"
    FAILED=1
    return
  fi

  # Convert the trace id to both backend forms per Skill 04c.
  local forms client_form bare_id
  forms=$(convert_trace_id_to_assessments_forms "$PROBE3_TRACE_ID")
  client_form="${forms%%$'\t'*}"
  bare_id="${forms##*$'\t'}"
  echo "  -> client form: $client_form" >&2
  echo "  -> bare id:     $bare_id" >&2

  # Step A: log a thumbs-up via the AppKit feedback route so we have a fresh
  # assessment to read back. The route is documented in 08-appkit-feedback.
  # If it doesn't exist on this AppKit App, fall through to read back any
  # assessment the agent itself emitted on the trace (Pathway-C agents may
  # log feedback server-side).
  local feedback_url="${APPKIT_URL}/api/feedback"
  local feedback_body
  feedback_body=$(jq -nc \
    --arg trace "$client_form" \
    --arg email "$EXPECTED_EMAIL" \
    '{trace_id: $trace, is_positive: true, rationale: "four-probe identity assertion"}')
  local feedback_resp feedback_code
  feedback_resp=$(curl -s -w "\n__HTTP_CODE__%{http_code}" \
    -X POST "$feedback_url" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-forwarded-email: $EXPECTED_EMAIL" \
    --max-time 60 \
    -d "$feedback_body" 2>/dev/null \
    || echo -e "\n__HTTP_CODE__000")
  feedback_code=$(echo "$feedback_resp" | grep -o '__HTTP_CODE__[0-9]*$' | sed 's/__HTTP_CODE__//' | tail -1)
  echo "  -> POST $feedback_url -> HTTP ${feedback_code:-000}" >&2
  # Non-200 from the feedback route is a soft signal — the agent may write
  # feedback server-side. Continue and attempt the SQL read-back.

  # Step B: read assessment.source_id back from the SQL warehouse using the
  # bare id form (Skill 04c documents the warehouse stores `trace_id` as the
  # bare id). Try the client form too in case the runtime persisted as URI.
  local sql_query
  sql_query=$(cat <<SQL
SELECT source_id
FROM ${MLFLOW_TRACING_TABLE}_assessments
WHERE trace_id IN ('${bare_id}', '${client_form}')
  AND name = 'user_feedback'
ORDER BY create_time_ms DESC
LIMIT 1
SQL
)

  if ! command -v databricks >/dev/null 2>&1; then
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: databricks CLI required for SQL read-back"
    FAILED=1
    return
  fi

  local sql_out source_id
  sql_out=$(databricks api post /api/2.0/sql/statements \
    --profile "$PROFILE" \
    --json "$(jq -nc \
      --arg q "$sql_query" \
      --arg w "$MLFLOW_TRACING_SQL_WAREHOUSE_ID" \
      '{statement: $q, warehouse_id: $w, wait_timeout: "30s"}')" \
    2>/dev/null \
    || echo "")

  if [ -z "$sql_out" ]; then
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: SQL statement API call failed (no response from /api/2.0/sql/statements)"
    FAILED=1
    return
  fi

  source_id=$(echo "$sql_out" | jq -r '.result.data_array[0][0] // empty' 2>/dev/null || true)

  if [ -z "$source_id" ]; then
    add_identity_result "$probe_name" "fail" \
      "trace_assessment_api_contract_missing: no assessment row found for trace ${bare_id} (warehouse lag, missing assessments table, or feedback path never wrote a row)"
    FAILED=1
    return
  fi

  if [ "$source_id" = "$EXPECTED_EMAIL" ]; then
    echo "  -> source_id=$source_id matches expected email -> PASS" >&2
    add_identity_result "$probe_name" "pass" \
      "source_id=$source_id matches EXPECTED_USER_EMAIL"
  else
    echo "  -> source_id=$source_id != EXPECTED_USER_EMAIL=$EXPECTED_EMAIL -> FAIL" >&2
    # The classic Pathway-C bug: source_id is the AppKit SP UUID instead of
    # the originating user email. This means x-app-user-email was not
    # forwarded (or the agent ignored it).
    add_identity_result "$probe_name" "fail" \
      "source_id=${source_id} != EXPECTED_USER_EMAIL=${EXPECTED_EMAIL} (likely AppKit SP UUID — x-app-user-email not forwarded or agent ignored it)"
    FAILED=1
  fi
}

run_probe "agent_direct"    "${AGENT_URL}/invocations" ""
run_probe "appkit_sp_only"  "${APPKIT_URL}/api/chat" ""
run_probe "appkit_with_obo" "${APPKIT_URL}/api/chat" "x-forwarded-access-token: $STUB_USER_TOKEN"
run_feedback_source_id_probe

RESULTS+="]"
echo "$RESULTS"

exit $FAILED

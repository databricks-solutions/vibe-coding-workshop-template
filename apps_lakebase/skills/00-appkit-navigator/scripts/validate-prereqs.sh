#!/usr/bin/env bash
# Validates all prerequisites for the AppKit + Lakebase workshop.
#
# Usage: bash scripts/validate-prereqs.sh [--profile PROFILE]
#
# Output: JSON to stdout, diagnostics to stderr.
# Exit codes: 0 = all pass, 1 = one or more failed.
set -euo pipefail

MIN_CLI_VERSION="0.295.0"
MIN_NODE_MAJOR=22
PROFILE=""

show_help() {
  cat <<'EOF'
Usage: bash scripts/validate-prereqs.sh [OPTIONS]

Validates prerequisites for the Databricks AppKit + Lakebase workshop.

Options:
  --profile PROFILE   Databricks CLI profile to validate (optional)
  --help, -h          Show this help message

Checks:
  - Databricks CLI >= 0.295.0
  - Node.js >= v22
  - git available
  - CLI profile authentication (if --profile given)

Output (JSON to stdout):
  { "cli": "ok|fail", "cli_version": "...", "node": "ok|fail", "node_version": "...",
    "git": "ok|fail", "auth": "ok|fail|skip", "profile": "..." }

Exit codes:
  0  All checks passed
  1  One or more checks failed (details in JSON output)

Idempotent: safe to run multiple times.
EOF
  exit 0
}

version_gte() {
  printf '%s\n%s' "$1" "$2" | sort -V | head -n1 | grep -qx "$2"
}

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

FAILED=0

# --- Check Databricks CLI ---
CLI_STATUS="fail"
CLI_VERSION=""
if command -v databricks &>/dev/null; then
  CLI_VERSION=$(databricks --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  if [ -n "$CLI_VERSION" ] && version_gte "$CLI_VERSION" "$MIN_CLI_VERSION"; then
    CLI_STATUS="ok"
    echo "Databricks CLI $CLI_VERSION (>= $MIN_CLI_VERSION) — OK" >&2
  else
    echo "Databricks CLI $CLI_VERSION is below minimum $MIN_CLI_VERSION" >&2
    FAILED=1
  fi
else
  echo "Databricks CLI not found. Install: https://docs.databricks.com/aws/en/dev-tools/cli/tutorial" >&2
  FAILED=1
fi

# --- Check Node.js ---
NODE_STATUS="fail"
NODE_VERSION=""
if command -v node &>/dev/null; then
  NODE_VERSION=$(node --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
  if [ "$NODE_MAJOR" -ge "$MIN_NODE_MAJOR" ]; then
    NODE_STATUS="ok"
    echo "Node.js v$NODE_VERSION (>= v$MIN_NODE_MAJOR) — OK" >&2
  else
    echo "Node.js v$NODE_VERSION is below minimum v$MIN_NODE_MAJOR" >&2
    FAILED=1
  fi
else
  echo "Node.js not found. Install: https://nodejs.org/" >&2
  FAILED=1
fi

# --- Check git ---
GIT_STATUS="fail"
if command -v git &>/dev/null; then
  GIT_STATUS="ok"
  echo "git — OK" >&2
else
  echo "git not found." >&2
  FAILED=1
fi

# --- Check CLI auth ---
AUTH_STATUS="skip"
if [ -n "$PROFILE" ]; then
  AUTH_STATUS="fail"
  if databricks auth token --profile "$PROFILE" &>/dev/null; then
    AUTH_STATUS="ok"
    echo "Auth profile '$PROFILE' — OK" >&2
  else
    echo "Auth profile '$PROFILE' — FAILED (run: databricks auth login --host <URL>)" >&2
    FAILED=1
  fi
fi

# --- Output JSON ---
cat <<EOF
{"cli":"$CLI_STATUS","cli_version":"$CLI_VERSION","node":"$NODE_STATUS","node_version":"$NODE_VERSION","git":"$GIT_STATUS","auth":"$AUTH_STATUS","profile":"$PROFILE"}
EOF

exit $FAILED

#!/usr/bin/env bash
# Installs Databricks Agent Skills for AI coding assistants.
#
# UPSTREAM: https://github.com/databricks/databricks-agent-skills
# Always check the upstream README for the latest installation method.
# This script is a convenience fallback when the repo cannot be reached
# directly from an IDE-native command.
#
# Strategy:
#   1. Always clone into .agents/skills/ (agentskills.io standard, works in all IDEs)
#   2. Optionally run IDE-native install for deeper integration
set -euo pipefail

REPO_URL="https://github.com/databricks/databricks-agent-skills"
AGENTS_SKILLS_DIR=".agents/skills/databricks-skills"
MIN_CLI_VERSION="0.295.0"

version_gte() {
  printf '%s\n%s' "$1" "$2" | sort -V | head -n1 | grep -qx "$2"
}

check_databricks_cli() {
  if ! command -v databricks &>/dev/null; then
    echo "Error: Databricks CLI is not installed."
    echo "Install it: https://docs.databricks.com/aws/en/dev-tools/cli/tutorial"
    exit 1
  fi

  CURRENT_VERSION=$(databricks --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not determine Databricks CLI version."
    echo "Run: databricks --version"
    exit 1
  fi

  if ! version_gte "$CURRENT_VERSION" "$MIN_CLI_VERSION"; then
    echo "Error: Databricks CLI version $CURRENT_VERSION is below minimum $MIN_CLI_VERSION."
    echo "Update: https://docs.databricks.com/aws/en/dev-tools/cli/tutorial"
    exit 1
  fi

  echo "Databricks CLI $CURRENT_VERSION (>= $MIN_CLI_VERSION) — OK"
}

check_node() {
  if ! command -v node &>/dev/null; then
    echo "Warning: Node.js not found. AppKit requires Node.js v22+."
    echo "Install: https://nodejs.org/"
  else
    NODE_MAJOR=$(node --version | grep -oE '[0-9]+' | head -1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
      echo "Warning: Node.js v${NODE_MAJOR} detected. AppKit requires v22+."
    else
      echo "Node.js $(node --version) — OK"
    fi
  fi
}

install_project_level() {
  if [ -d "$AGENTS_SKILLS_DIR/skills" ]; then
    echo "Agent Skills already present at $AGENTS_SKILLS_DIR — skipping clone."
    return 0
  fi

  if ! command -v git &>/dev/null; then
    echo "Error: git is not installed. Cannot clone agent skills."
    exit 1
  fi

  echo "Cloning agent skills into $AGENTS_SKILLS_DIR ..."
  git clone --depth 1 "$REPO_URL" "$AGENTS_SKILLS_DIR"
  echo "Agent Skills installed to $AGENTS_SKILLS_DIR"
}

install_ide_extra() {
  if [ -n "${CLAUDE_CODE:-}" ] || [ -d "$HOME/.claude" ]; then
    echo "Claude Code detected — also installing to ~/.claude/skills/ ..."
    databricks experimental aitools skills install 2>/dev/null || echo "  (IDE-native install skipped — project-level clone is sufficient)"
  elif [ -n "${CURSOR_TRACE_ID:-}" ] || [ -d "$HOME/.cursor" ]; then
    echo ""
    echo "Cursor detected — optionally also run in Cursor chat:"
    echo "  /add-plugin databricks-skills"
    echo ""
  fi
}

# --- Main ---

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: bash scripts/install-agent-skills.sh"
  echo ""
  echo "Installs Databricks Agent Skills for AI coding assistants."
  echo "  - Clones skills into .agents/skills/databricks-skills (all IDEs)"
  echo "  - Optionally runs IDE-native install for Cursor/Claude Code"
  echo ""
  echo "Prerequisites: git, Databricks CLI >= 0.295.0, Node.js v22+"
  echo "Idempotent: safe to run multiple times."
  exit 0
fi

check_databricks_cli
check_node

echo ""
echo "Installing agent skills to project (.agents/skills/) ..."
install_project_level

echo ""
echo "Checking for IDE-native extras ..."
install_ide_extra

echo ""
echo "Verification — CLI tools should be available:"
echo "  databricks experimental aitools tools --help"
echo ""
echo "Done."

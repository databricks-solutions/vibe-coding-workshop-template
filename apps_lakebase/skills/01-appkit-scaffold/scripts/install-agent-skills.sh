#!/usr/bin/env bash
# Installs Databricks Agent Skills for AI coding assistants.
#
# UPSTREAM: https://github.com/databricks/databricks-agent-skills
# Always check the upstream README for the latest installation method.
# This script is a convenience fallback when the repo cannot be reached
# directly from an IDE-native command.
#
# CLIENT NOTE — the default flow is IDE/CLI ONLY. It assumes a local Databricks
# CLI (`databricks --version`) and the `aitools install` verb, both of which are
# HARD-BLOCKED on Genie Code. On Genie Code the Databricks skills are already
# loaded in-session, so the default flow is not used; instead the Genie Code path
# is a two-location first-run kickstart: git clone the workshop repo into your
# user project (= artifact_root, git-backed so generated bundles are recognized),
# then copy the tree into your per-user skills folder
# `/Workspace/Users/<your-username>/.assistant/skills/` (Genie Code recurses there
# to discover every skill). Run `bash install-agent-skills.sh --genie-code` to
# print it; it is also documented in the repo-root AGENTS.md "Genie Code" section.
#
# Strategy (IDE/CLI):
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
    databricks aitools install 2>/dev/null || echo "  (IDE-native install skipped — project-level clone is sufficient)"
  elif [ -n "${CURSOR_TRACE_ID:-}" ] || [ -d "$HOME/.cursor" ]; then
    echo ""
    echo "Cursor detected — optionally also run in Cursor chat:"
    echo "  /add-plugin databricks-skills"
    echo ""
  fi
}

# --- Main ---

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: bash scripts/install-agent-skills.sh [--genie-code]"
  echo ""
  echo "Installs Databricks Agent Skills for AI coding assistants."
  echo "  - Clones skills into .agents/skills/databricks-skills (all IDEs)"
  echo "  - Optionally runs IDE-native install for Cursor/Claude Code"
  echo ""
  echo "  --genie-code   Print the Genie Code clone+copy kickstart and exit"
  echo "                 (no local CLI/Node/auth — Genie Code is pre-authenticated)"
  echo ""
  echo "Prerequisites (default IDE/CLI flow): git, Databricks CLI >= 0.295.0, Node.js v22+"
  echo "Idempotent: safe to run multiple times."
  exit 0
fi

# Genie Code path: no local CLI/Node/auth (pre-authenticated, in-workspace).
# Genie Code discovers skills by recursing into the skills-folder COPY of this
# repo — so the kickstart clones the repo into the user project (git-backed, for
# bundle recognition) and copies the tree into the per-user skills folder.
if [[ "${1:-}" == "--genie-code" ]]; then
  cat <<'EOF'
Genie Code path — pre-authenticated, in-workspace, serverless (no local CLI/Node).
Genie Code needs the workshop repo in TWO places: a git clone in your user
project (so generated bundles are recognized — bundle recognition requires a git
working tree) and a copy in your per-user skills folder (where Genie Code recurses
to discover every skill). Run this once (first-run kickstart):

  # 1. git clone the workshop repo INTO your user project (= artifact_root, git-backed)
  git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git \
    /Workspace/Users/<your-username>/vibe-coding-workshop

  # 2. copy the tree into your per-user skills folder for discovery (no git needed here)
  cp -r /Workspace/Users/<your-username>/vibe-coding-workshop \
    /Workspace/Users/<your-username>/.assistant/skills/vibe-coding-workshop

Then load skills/genie-code-environment (the behavior manifest). The default
IDE/CLI flow below is NOT used on Genie Code (its CLI checks are hard-blocked).
See the repo-root AGENTS.md "Genie Code" section and PRE-REQUISITES.md.
EOF
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
echo "  databricks aitools tools --help"
echo ""
echo "Done."

#!/usr/bin/env bash
# Installs Databricks Agent Skills for AI coding assistants.
#
# UPSTREAM: https://github.com/databricks/databricks-agent-skills
# Always check the upstream README for the latest installation method.
# This script is a convenience fallback when the repo cannot be reached.
set -euo pipefail

MIN_VERSION="0.295.0"

version_gte() {
  printf '%s\n%s' "$1" "$2" | sort -V | head -n1 | grep -qx "$2"
}

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

if ! version_gte "$CURRENT_VERSION" "$MIN_VERSION"; then
  echo "Error: Databricks CLI version $CURRENT_VERSION is below minimum $MIN_VERSION."
  echo "Update: https://docs.databricks.com/aws/en/dev-tools/cli/tutorial"
  exit 1
fi

echo "Databricks CLI $CURRENT_VERSION (>= $MIN_VERSION) — OK"

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

echo "Installing Databricks Agent Skills..."
databricks experimental aitools install

echo "Agent Skills installed successfully."
echo "Available tools: databricks experimental aitools tools --help"

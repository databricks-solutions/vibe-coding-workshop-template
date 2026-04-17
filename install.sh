#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---------------------------------------------------------------------------
# Homebrew
# ---------------------------------------------------------------------------
if command -v brew &>/dev/null; then
    info "Homebrew already installed ($(brew --version | head -1))"
else
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

info "Updating Homebrew..."
brew update && brew upgrade

# ---------------------------------------------------------------------------
# Helper: install or upgrade a brew formula
# ---------------------------------------------------------------------------
brew_install_or_upgrade() {
    local formula="$1"
    if brew list --formula | grep -q "^${formula}\$"; then
        info "${formula} already installed — upgrading..."
        brew upgrade "$formula" 2>/dev/null || info "${formula} already at latest version"
    else
        info "Installing ${formula}..."
        brew install "$formula"
    fi
}

# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------
brew_install_or_upgrade git
brew_install_or_upgrade python3
brew_install_or_upgrade node

# ---------------------------------------------------------------------------
# Databricks CLI (custom tap)
# ---------------------------------------------------------------------------
if ! brew tap | grep -q "^databricks/tap\$"; then
    info "Tapping databricks/tap..."
    brew tap databricks/tap
fi
brew_install_or_upgrade databricks

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
info "Installation complete. Versions installed:"
echo "  git        : $(git --version)"
echo "  python3    : $(python3 --version)"
echo "  node       : $(node --version)"
echo "  databricks : $(databricks --version 2>/dev/null || echo 'check manually')"
echo ""

if [[ -f /opt/homebrew/bin/brew ]]; then
    SHELL_RC="${HOME}/.zshrc"
    if ! grep -q '/opt/homebrew/bin/brew' "$SHELL_RC" 2>/dev/null; then
        warn "Add this line to ${SHELL_RC} so brew is on your PATH in new shells:"
        echo '  eval "$(/opt/homebrew/bin/brew shellenv)"'
    fi
fi

info "Done."

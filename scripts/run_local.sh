#!/bin/bash
# ============================================================================
# Run App Locally Script
# Test your app locally before deploying to Databricks
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🧪 Running App Locally"
echo "======================"
echo ""

# Load environment
if [ -f ".env.local" ]; then
    source .env.local
    export DATABRICKS_HOST
    export DATABRICKS_TOKEN
    export DATABRICKS_CONFIG_PROFILE
fi

# Build frontend first (if exists)
if [ -d "client" ] && [ -f "client/package.json" ]; then
    echo -e "${BLUE}📦 Building frontend...${NC}"
    cd client
    if command -v bun &> /dev/null; then
        bun run build
    else
        npm run build
    fi
    cd ..
    echo -e "${GREEN}✓ Frontend built${NC}"
    echo ""
fi

# Run the app in production mode locally
echo -e "${BLUE}🚀 Starting app in production mode...${NC}"
echo ""

if command -v uv &> /dev/null; then
    uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
else
    python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
fi


#!/bin/bash
# ============================================================================
# Databricks App Status Script
# Check the status of your deployed Databricks App
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
VERBOSE=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --verbose) VERBOSE=true ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --verbose  Include full JSON response and workspace files"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Load environment
if [ ! -f ".env.local" ]; then
    echo -e "${RED}❌ .env.local not found. Run ./scripts/setup.sh first${NC}"
    exit 1
fi

source .env.local

# Set up authentication
if [ "$DATABRICKS_AUTH_TYPE" = "pat" ]; then
    export DATABRICKS_HOST
    export DATABRICKS_TOKEN
else
    export DATABRICKS_CONFIG_PROFILE
fi

APP_NAME="${DATABRICKS_APP_NAME:-my-databricks-app}"

echo ""
echo -e "${CYAN}📊 Databricks App Status${NC}"
echo "========================"
echo ""

# Get app info
APP_INFO=$(databricks apps get "$APP_NAME" --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ App '$APP_NAME' not found${NC}"
    echo ""
    echo "Available apps:"
    databricks apps list --output table
    exit 1
fi

# Parse and display status
APP_URL=$(echo "$APP_INFO" | jq -r '.url // "N/A"')
APP_STATE=$(echo "$APP_INFO" | jq -r '.status.state // "UNKNOWN"')
COMPUTE_STATE=$(echo "$APP_INFO" | jq -r '.computeStatus.state // "UNKNOWN"')
LAST_DEPLOYED=$(echo "$APP_INFO" | jq -r '.activeDeployment.updateTime // "Never"')

# Status color
case $APP_STATE in
    "RUNNING") STATE_COLOR=$GREEN ;;
    "PENDING"|"STARTING") STATE_COLOR=$YELLOW ;;
    *) STATE_COLOR=$RED ;;
esac

case $COMPUTE_STATE in
    "ACTIVE") COMPUTE_COLOR=$GREEN ;;
    "STARTING"|"PENDING") COMPUTE_COLOR=$YELLOW ;;
    *) COMPUTE_COLOR=$RED ;;
esac

echo -e "${BLUE}App Name:${NC}      $APP_NAME"
echo -e "${BLUE}App URL:${NC}       $APP_URL"
echo -e "${BLUE}App State:${NC}     ${STATE_COLOR}${APP_STATE}${NC}"
echo -e "${BLUE}Compute State:${NC} ${COMPUTE_COLOR}${COMPUTE_STATE}${NC}"
echo -e "${BLUE}Last Deployed:${NC} $LAST_DEPLOYED"
echo ""

# Show logs URL
if [ "$APP_URL" != "N/A" ] && [ "$APP_URL" != "null" ]; then
    echo -e "${BLUE}📋 View Logs:${NC} ${APP_URL}/logz"
    echo "   (Open in browser - requires OAuth authentication)"
    echo ""
fi

# Verbose output
if [ "$VERBOSE" = true ]; then
    echo -e "${CYAN}Full App Info (JSON):${NC}"
    echo "---------------------"
    echo "$APP_INFO" | jq '.'
    echo ""
    
    # List workspace files
    SOURCE_PATH="${DBA_SOURCE_CODE_PATH:-/Workspace/Users/$(databricks current-user me --output json | jq -r '.userName')/${APP_NAME}}"
    
    echo -e "${CYAN}Workspace Files:${NC}"
    echo "----------------"
    databricks workspace list "$SOURCE_PATH" --output table 2>/dev/null || echo "  (Unable to list files)"
    echo ""
fi

# Quick actions
echo -e "${CYAN}Quick Actions:${NC}"
echo "  Redeploy:    ./scripts/deploy.sh"
echo "  View logs:   Open ${APP_URL}/logz in browser"
echo "  Test local:  ./scripts/run_local.sh"
echo ""


#!/bin/bash
# ============================================================================
# Databricks App Deployment Script
# Deploys your application to Databricks Apps platform
# ============================================================================
#
# USAGE:
#   ./scripts/deploy.sh                       # Deploy app only
#   ./scripts/deploy.sh --create              # First deploy (creates app)
#   ./scripts/deploy.sh --with-lakebase       # Deploy app + setup Lakebase tables
#   ./scripts/deploy.sh --lakebase-only       # Only setup Lakebase tables
#   ./scripts/deploy.sh --setup-permissions   # Setup all Lakebase permissions
#   ./scripts/deploy.sh --full                # Full setup: deploy + permissions + tables
#   ./scripts/deploy.sh --verbose             # Detailed output
#
# PERMISSION TYPES:
#   1. Unity Catalog:  ALL_PRIVILEGES on catalog (for schema/table access)
#   2. Database Role:  DATABRICKS_SUPERUSER (for PostgreSQL operations)
#   3. App Resource:   CAN_CONNECT_AND_CREATE (for automatic PGPASSWORD)
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse arguments
CREATE_APP=false
VERBOSE=false
WITH_LAKEBASE=false
LAKEBASE_ONLY=false
SETUP_PERMISSIONS=false
FULL_SETUP=false
CATALOG=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --create) CREATE_APP=true ;;
        --verbose) VERBOSE=true ;;
        --with-lakebase) WITH_LAKEBASE=true ;;
        --lakebase-only) LAKEBASE_ONLY=true ;;
        --setup-permissions) SETUP_PERMISSIONS=true ;;
        --full) FULL_SETUP=true ;;
        --catalog)
            CATALOG="$2"
            shift
            ;;
        -h|--help)
            echo ""
            echo "Databricks App Deployment"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --create              Create app if it doesn't exist (required for first deploy)"
            echo "  --verbose             Show detailed deployment logs"
            echo "  --with-lakebase       Also setup Lakebase tables after deployment"
            echo "  --lakebase-only       Only setup Lakebase tables (skip app deployment)"
            echo "  --setup-permissions   Setup all Lakebase permissions (requires --catalog)"
            echo "  --full                Full setup: deploy + permissions + tables (requires --catalog)"
            echo "  --catalog <name>      Catalog name for permission setup"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --create                           # First deployment (creates app)"
            echo "  $0                                    # Update existing app"
            echo "  $0 --with-lakebase                    # Deploy app + Lakebase tables"
            echo "  $0 --lakebase-only                    # Only setup Lakebase tables"
            echo "  $0 --setup-permissions --catalog my_catalog  # Setup all permissions"
            echo "  $0 --full --catalog my_catalog        # Full deployment with permissions"
            echo "  $0 --verbose                          # Deploy with detailed output"
            echo ""
            echo "Permission commands (via lakebase_manager.py):"
            echo "  python scripts/lakebase_manager.py --action setup-all-permissions --catalog <name>"
            echo "  python scripts/lakebase_manager.py --action add-lakebase-role"
            echo "  python scripts/lakebase_manager.py --action add-app-resource"
            echo ""
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# If --full is set, enable all features
if [ "$FULL_SETUP" = true ]; then
    CREATE_APP=true
    SETUP_PERMISSIONS=true
    WITH_LAKEBASE=true
fi

echo ""
echo "🚀 Databricks App Deployment"
echo "============================"
echo ""

# ============================================================================
# Handle Lakebase-only mode
# ============================================================================
if [ "$LAKEBASE_ONLY" = true ]; then
    echo -e "${BLUE}🌊 Lakebase Setup Only${NC}"
    echo ""
    
    if [ -f "scripts/setup-lakebase.sh" ]; then
        ./scripts/setup-lakebase.sh --recreate
        echo ""
        echo -e "${GREEN}✓ Lakebase setup complete${NC}"
    else
        echo -e "${RED}❌ setup-lakebase.sh not found${NC}"
        exit 1
    fi
    exit 0
fi

# ============================================================================
# Load Environment
# ============================================================================
if [ ! -f ".env.local" ]; then
    echo -e "${RED}❌ .env.local not found${NC}"
    echo ""
    echo "Run setup first:"
    echo "  ./scripts/setup.sh"
    echo ""
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

echo -e "${BLUE}App Name:${NC} ${APP_NAME}"
echo ""

# ============================================================================
# Step 1: Build Frontend (if exists)
# ============================================================================
if [ -d "client" ] && [ -f "client/package.json" ]; then
    echo -e "${BLUE}📦 Step 1: Building frontend...${NC}"
    cd client
    if command -v bun &> /dev/null; then
        bun run build
    elif command -v npm &> /dev/null; then
        npm run build
    else
        echo -e "${YELLOW}⚠ No npm/bun found - skipping frontend build${NC}"
    fi
    cd ..
    echo -e "${GREEN}✓ Frontend built${NC}"
    echo ""
else
    echo -e "${BLUE}📦 Step 1: No frontend to build (client/ not found)${NC}"
    echo ""
fi

# ============================================================================
# Step 2: Generate requirements.txt
# ============================================================================
echo -e "${BLUE}📋 Step 2: Generating requirements.txt...${NC}"

if [ -f "scripts/generate_requirements.py" ]; then
    python3 scripts/generate_requirements.py
else
    echo -e "${YELLOW}⚠ generate_requirements.py not found${NC}"
    echo "  Creating basic requirements.txt from pyproject.toml..."
    
    # Simple fallback
    if command -v uv &> /dev/null; then
        uv pip compile pyproject.toml -o requirements.txt --quiet 2>/dev/null || true
    fi
fi

if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓ requirements.txt ready${NC}"
else
    echo -e "${YELLOW}⚠ No requirements.txt - dependencies may not install correctly${NC}"
fi
echo ""

# ============================================================================
# Step 3: Create App (if requested)
# ============================================================================
if [ "$CREATE_APP" = true ]; then
    echo -e "${BLUE}🔧 Step 3: Creating Databricks App...${NC}"
    
    # Check if app exists
    if databricks apps get "$APP_NAME" &> /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ App '${APP_NAME}' already exists - skipping creation${NC}"
    else
        echo "  Creating app: $APP_NAME"
        databricks apps create "$APP_NAME" --description "Deployed via vibe coding template"
        echo -e "${GREEN}✓ App created${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}🔧 Step 3: Skipping app creation (use --create for first deploy)${NC}"
    echo ""
fi

# ============================================================================
# Step 4: Sync Source Code to Workspace
# ============================================================================
echo -e "${BLUE}📤 Step 4: Syncing source code to workspace...${NC}"

# Get the source code path for the app
if [ -n "$DBA_SOURCE_CODE_PATH" ]; then
    SOURCE_PATH="$DBA_SOURCE_CODE_PATH"
else
    # Get current user email for default path
    if command -v jq &> /dev/null; then
        USER_NAME=$(databricks current-user me --output json | jq -r '.userName')
    else
        USER_NAME=$(databricks current-user me --output json | grep -o '"userName":"[^"]*"' | cut -d'"' -f4)
    fi
    SOURCE_PATH="/Workspace/Users/${USER_NAME}/${APP_NAME}"
fi

echo "  Target: $SOURCE_PATH"

# Create directory if needed
databricks workspace mkdirs "$SOURCE_PATH" 2>/dev/null || true

# Sync files (excluding unnecessary files)
SYNC_EXCLUDE="--exclude .git --exclude .env.local --exclude .env --exclude __pycache__ --exclude node_modules --exclude .venv --exclude .pytest_cache --exclude .mypy_cache --exclude .ruff_cache --exclude *.pyc"

if [ "$VERBOSE" = true ]; then
    echo "  Syncing files..."
    databricks sync . "$SOURCE_PATH" $SYNC_EXCLUDE
else
    databricks sync . "$SOURCE_PATH" $SYNC_EXCLUDE 2>&1 | grep -E "^(Uploading|Deleting)" | head -10 || true
fi

echo -e "${GREEN}✓ Source code synced${NC}"
echo ""

# ============================================================================
# Step 4b: Sync Frontend Build (excluded from .gitignore)
# ============================================================================
if [ -d "client/build" ] && [ -f "client/build/index.html" ]; then
    echo -e "${BLUE}📦 Step 4b: Syncing frontend build...${NC}"
    databricks workspace mkdirs "$SOURCE_PATH/client/build" 2>/dev/null || true
    databricks workspace import-dir client/build "$SOURCE_PATH/client/build" --overwrite
    echo -e "${GREEN}✓ Frontend build synced${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ No frontend build found (client/build/index.html missing)${NC}"
    echo "  Run 'npm run build' in the client directory first"
    echo ""
fi

# ============================================================================
# Step 5: Deploy the App
# ============================================================================
echo -e "${BLUE}🚀 Step 5: Deploying app...${NC}"

if [ "$VERBOSE" = true ]; then
    databricks apps deploy "$APP_NAME" --source-code-path "$SOURCE_PATH"
else
    databricks apps deploy "$APP_NAME" --source-code-path "$SOURCE_PATH" 2>&1 | tail -10
fi

echo -e "${GREEN}✓ Deployment initiated${NC}"
echo ""

# ============================================================================
# Step 6: Setup Lakebase Permissions (Optional)
# ============================================================================
if [ "$SETUP_PERMISSIONS" = true ]; then
    echo -e "${BLUE}🔐 Step 6: Setting up Lakebase permissions...${NC}"
    
    if [ -z "$CATALOG" ]; then
        echo -e "${YELLOW}⚠ --catalog is required for permission setup${NC}"
        echo "  Usage: $0 --setup-permissions --catalog <catalog_name>"
        echo ""
    else
        if [ -f "scripts/lakebase_manager.py" ]; then
            echo "  Catalog: $CATALOG"
            echo ""
            
            # Run the permission setup
            python3 scripts/lakebase_manager.py --action setup-all-permissions --catalog "$CATALOG"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Permissions configured${NC}"
            else
                echo -e "${YELLOW}⚠ Some permissions may need manual setup${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ lakebase_manager.py not found - skipping permission setup${NC}"
        fi
    fi
    echo ""
else
    echo -e "${BLUE}🔐 Step 6: Skipping permission setup (use --setup-permissions --catalog <name>)${NC}"
    echo ""
fi

# ============================================================================
# Step 7: Setup Lakebase Tables (Optional)
# ============================================================================
if [ "$WITH_LAKEBASE" = true ]; then
    echo -e "${BLUE}🌊 Step 7: Setting up Lakebase tables...${NC}"
    
    if [ -f "scripts/setup-lakebase.sh" ]; then
        # Check if DDL files exist
        DDL_COUNT=$(find db/lakebase/ddl -name "*.sql" 2>/dev/null | wc -l | tr -d ' ')
        
        if [ "$DDL_COUNT" -gt 0 ]; then
            ./scripts/setup-lakebase.sh --recreate
            echo -e "${GREEN}✓ Lakebase tables setup complete${NC}"
        else
            echo -e "${YELLOW}⚠ No DDL files found in db/lakebase/ddl/${NC}"
            echo "  Add your .sql files there to setup Lakebase tables"
        fi
    else
        echo -e "${YELLOW}⚠ setup-lakebase.sh not found - skipping Lakebase setup${NC}"
    fi
    echo ""
else
    echo -e "${BLUE}🌊 Step 7: Skipping Lakebase setup (use --with-lakebase to include)${NC}"
    echo ""
fi

# ============================================================================
# Step 8: Get App URL and Status
# ============================================================================
echo -e "${BLUE}📍 Step 8: Getting app status...${NC}"

# Wait a moment for deployment to register
sleep 2

APP_INFO=$(databricks apps get "$APP_NAME" --output json 2>/dev/null || echo "{}")

if command -v jq &> /dev/null; then
    APP_URL=$(echo "$APP_INFO" | jq -r '.url // "pending..."')
    APP_STATE=$(echo "$APP_INFO" | jq -r '.status.state // "UNKNOWN"')
else
    APP_URL=$(echo "$APP_INFO" | grep -o '"url":"[^"]*"' | cut -d'"' -f4 || echo "pending...")
    APP_STATE="Check status with: ./scripts/app_status.sh"
fi

echo ""
echo "============================================"
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo "============================================"
echo ""
echo "  App Name:   $APP_NAME"
echo "  App URL:    $APP_URL"
echo "  Status:     $APP_STATE"
echo ""
echo "Next steps:"
echo ""
echo "  • View app:            Open $APP_URL in browser"
echo "  • View logs:           ${APP_URL}/logz (requires browser auth)"
echo "  • Check status:        ./scripts/app_status.sh"
echo "  • Redeploy:            ./scripts/deploy.sh"
echo ""
echo "Lakebase commands:"
echo ""
echo "  • Setup tables:        ./scripts/deploy.sh --lakebase-only"
echo "  • Deploy + Lakebase:   ./scripts/deploy.sh --with-lakebase"
echo "  • Check Lakebase:      python scripts/lakebase_manager.py --action status"
echo ""
echo "Permission commands:"
echo ""
echo "  • Setup all perms:     python scripts/lakebase_manager.py --action setup-all-permissions --catalog <name>"
echo "  • Add database role:   python scripts/lakebase_manager.py --action add-lakebase-role"
echo "  • Link app resource:   python scripts/lakebase_manager.py --action add-app-resource"
echo "  • Full deploy:         ./scripts/deploy.sh --full --catalog <name>"
echo ""

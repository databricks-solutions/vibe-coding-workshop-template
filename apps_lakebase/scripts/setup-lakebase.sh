#!/bin/bash
# =============================================================================
# Vibe Coding Workshop - Lakebase Table Setup
# =============================================================================
#
# Creates or recreates the tables in Lakebase using Python/psycopg2.
# Optionally creates the Lakebase instance if it doesn't exist.
# Reads DDL from db/lakebase/ddl/*.sql
# Reads DML seed data from db/lakebase/dml_seed/*.sql
#
# USAGE:
#   ./scripts/setup-lakebase.sh                      # Create tables if not exist + seed
#   ./scripts/setup-lakebase.sh --recreate           # Drop and recreate tables + seed
#   ./scripts/setup-lakebase.sh --drop               # Drop tables only
#   ./scripts/setup-lakebase.sh --status             # Check table status
#   ./scripts/setup-lakebase.sh --check-instance     # Check if Lakebase instance exists
#   ./scripts/setup-lakebase.sh --create-instance    # Create Lakebase instance if not exists
#   ./scripts/setup-lakebase.sh --setup-permissions  # Setup app permissions on Lakebase
#   ./scripts/setup-lakebase.sh --full-setup         # Full setup: instance + permissions + tables
#
# REQUIREMENTS:
#   - Python with psycopg (v3) or psycopg2-binary, requests
#   - databricks CLI (authenticated)
#   - databricks-sdk (Python)
#
# SQL FILES:
#   db/lakebase/ddl/           - Table definitions (PostgreSQL syntax)
#   db/lakebase/dml_seed/      - Seed data (will be transformed from Spark to PG)
#
# LAKEBASE MODES:
#   autoscaling  - Uses ENDPOINT_NAME + generate_database_credential (preferred)
#   provisioned  - Uses OAuth token directly as Postgres password (legacy)
#   Mode is auto-detected from ENDPOINT_NAME format (projects/... = autoscaling)
#
# CONFIGURATION (environment variables):
#   DATABRICKS_HOST             - Workspace URL (default from app.yaml)
#   LAKEBASE_INSTANCE_NAME      - Instance name
#   APP_NAME                    - App name
#   LAKEBASE_MODE               - "autoscaling" or "provisioned" (auto-detected)
#   ENDPOINT_NAME               - Autoscaling endpoint path (from app.yaml)
#   PRODUCTION_SCHEMA           - Schema name that requires extra confirmation
#
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Default configuration
LAKEBASE_INSTANCE_NAME="${LAKEBASE_INSTANCE_NAME:-vibe-coding-workshop-lakebase}"
APP_NAME="${APP_NAME:-vibe-coding-workshop-app}"
DATABRICKS_HOST="${DATABRICKS_HOST:-}"
AUTO_APPROVE=false

# Parse arguments
ACTION="create"
SETUP_INSTANCE=false
SETUP_PERMISSIONS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --recreate)
            ACTION="recreate"
            shift
            ;;
        --drop)
            ACTION="drop"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --check-instance)
            ACTION="check-instance"
            shift
            ;;
        --create-instance)
            ACTION="create-instance"
            shift
            ;;
        --setup-permissions)
            ACTION="setup-permissions"
            shift
            ;;
        --full-setup)
            ACTION="full-setup"
            shift
            ;;
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --instance-name)
            LAKEBASE_INSTANCE_NAME="$2"
            shift 2
            ;;
        --yes|--auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🌊 Lakebase Setup${NC}"
echo ""
echo -e "Action: ${CYAN}${ACTION}${NC}"
echo ""

# =============================================================================
# Handle instance management actions (using lakebase_manager.py)
# =============================================================================

if [[ "$ACTION" == "check-instance" ]]; then
    echo -e "${BLUE}Checking Lakebase connection...${NC}"
    python3 "${PROJECT_ROOT}/scripts/lakebase_manager.py" \
        --action check \
        --app-name "$APP_NAME" \
        --instance-name "$LAKEBASE_INSTANCE_NAME" \
        --host "$DATABRICKS_HOST" \
        --project-root "$PROJECT_ROOT"
    exit $?
fi

if [[ "$ACTION" == "setup-permissions" ]]; then
    echo -e "${BLUE}Getting permission setup instructions...${NC}"
    python3 "${PROJECT_ROOT}/scripts/lakebase_manager.py" \
        --action status \
        --app-name "$APP_NAME" \
        --instance-name "$LAKEBASE_INSTANCE_NAME" \
        --host "$DATABRICKS_HOST" \
        --project-root "$PROJECT_ROOT"
    exit $?
fi

if [[ "$ACTION" == "full-setup" ]]; then
    echo -e "${BLUE}Running full Lakebase setup...${NC}"
    echo ""
    
    # Step 1: Check connection and show status
    echo -e "${CYAN}Step 1: Status Check${NC}"
    python3 "${PROJECT_ROOT}/scripts/lakebase_manager.py" \
        --action status \
        --app-name "$APP_NAME" \
        --instance-name "$LAKEBASE_INSTANCE_NAME" \
        --host "$DATABRICKS_HOST" \
        --project-root "$PROJECT_ROOT"
    
    # Step 2: Create tables and seed data
    echo ""
    echo -e "${CYAN}Step 2: Table Setup${NC}"
    ACTION="recreate"  # Continue with table recreation
fi

# =============================================================================
# Get configuration - ENVIRONMENT VARIABLES TAKE PRIORITY over app.yaml
# =============================================================================
# IMPORTANT: When running via deploy.sh, environment variables should be set
# to match the target environment (development vs production)
# =============================================================================

get_yaml_value() {
    local key=$1
    grep -A1 "name: $key" app.yaml | grep "value:" | sed 's/.*value: *"\([^"]*\)".*/\1/' | head -1
}

# Use environment variables if set, otherwise fall back to app.yaml
if [[ -n "${LAKEBASE_HOST_OVERRIDE:-}" ]]; then
    LAKEBASE_HOST="$LAKEBASE_HOST_OVERRIDE"
else
    LAKEBASE_HOST=$(get_yaml_value "LAKEBASE_HOST")
fi

if [[ -n "${LAKEBASE_SCHEMA_OVERRIDE:-}" ]]; then
    LAKEBASE_SCHEMA="$LAKEBASE_SCHEMA_OVERRIDE"
else
    LAKEBASE_SCHEMA=$(get_yaml_value "LAKEBASE_SCHEMA")
fi

LAKEBASE_DATABASE="${LAKEBASE_DATABASE_OVERRIDE:-$(get_yaml_value "LAKEBASE_DATABASE")}"
LAKEBASE_PORT="${LAKEBASE_PORT_OVERRIDE:-$(get_yaml_value "LAKEBASE_PORT")}"

# Extract ENDPOINT_NAME and LAKEBASE_MODE (critical for autoscaling vs provisioned auth)
if [[ -z "${ENDPOINT_NAME:-}" ]]; then
    ENDPOINT_NAME=$(get_yaml_value "ENDPOINT_NAME")
fi
if [[ -z "${LAKEBASE_MODE:-}" ]]; then
    # Auto-detect mode: if ENDPOINT_NAME looks like "projects/..." it's autoscaling
    if [[ "${ENDPOINT_NAME:-}" == projects/* ]]; then
        LAKEBASE_MODE="autoscaling"
    else
        LAKEBASE_MODE="provisioned"
    fi
fi

# Get the current authenticated user from Databricks CLI (not from app.yaml)
# During deployment, setup-lakebase.sh runs as the deployer, not as the app's service principal
if [[ -n "${LAKEBASE_USER_OVERRIDE:-}" ]]; then
    LAKEBASE_USER="$LAKEBASE_USER_OVERRIDE"
else
    LAKEBASE_USER=$(databricks current-user me --output json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('userName',''))" 2>/dev/null) || true
    if [[ -z "$LAKEBASE_USER" ]]; then
        echo -e "${RED}Error: Could not determine current Databricks user${NC}"
        exit 1
    fi
fi

# Display configuration source
if [[ -n "${LAKEBASE_SCHEMA_OVERRIDE:-}" ]]; then
    echo -e "${YELLOW}⚠️  Using ENVIRONMENT VARIABLE overrides (not app.yaml)${NC}"
    echo ""
fi

echo -e "Configuration:"
echo -e "  Host:     ${BLUE}${LAKEBASE_HOST:0:50}...${NC}"
echo -e "  Database: ${BLUE}${LAKEBASE_DATABASE}${NC}"
echo -e "  Schema:   ${BLUE}${LAKEBASE_SCHEMA}${NC}"
echo -e "  Port:     ${BLUE}${LAKEBASE_PORT}${NC}"
echo -e "  User:     ${BLUE}${LAKEBASE_USER}${NC}"
echo -e "  Mode:     ${BLUE}${LAKEBASE_MODE}${NC}"
if [[ "$LAKEBASE_MODE" == "autoscaling" && -n "$ENDPOINT_NAME" ]]; then
    echo -e "  Endpoint: ${BLUE}${ENDPOINT_NAME}${NC}"
fi
echo ""

# SAFETY CHECK: Confirm recreate unless auto-approved
# Set PRODUCTION_SCHEMA env var to require extra confirmation for a specific schema
PRODUCTION_SCHEMA="${PRODUCTION_SCHEMA:-}"
if [[ "$ACTION" == "recreate" && "$AUTO_APPROVE" != true ]]; then
    if [[ -n "$PRODUCTION_SCHEMA" && "$LAKEBASE_SCHEMA" == "$PRODUCTION_SCHEMA" ]]; then
        echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}  ⚠️  WARNING: You are about to RECREATE tables in PRODUCTION!${NC}"
        echo -e "${RED}  Schema: $LAKEBASE_SCHEMA${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        read -p "Type 'YES-PRODUCTION' to confirm: " confirmation
        if [[ "$confirmation" != "YES-PRODUCTION" ]]; then
            echo -e "${RED}Aborted.${NC}"
            exit 1
        fi
    fi
fi

# =============================================================================
# Check prerequisites
# =============================================================================

if ! databricks current-user me &>/dev/null; then
    echo -e "${RED}Error: Not authenticated to Databricks${NC}"
    echo "Run: databricks auth login --host <your-workspace-url>"
    exit 1
fi

# Check if required Python packages are available (prefer psycopg3, fall back to psycopg2)
python3 -c "import psycopg" 2>/dev/null || python3 -c "import psycopg2" 2>/dev/null || {
    echo -e "${YELLOW}Installing psycopg[binary]...${NC}"
    pip3 install -q "psycopg[binary]" || pip3 install -q psycopg2-binary
}

python3 -c "import requests" 2>/dev/null || {
    echo -e "${YELLOW}Installing requests...${NC}"
    pip3 install -q requests
}

# =============================================================================
# Run Python script for database operations
# =============================================================================

# Export variables for Python
export LAKEBASE_HOST LAKEBASE_DATABASE LAKEBASE_SCHEMA LAKEBASE_PORT LAKEBASE_USER ACTION PROJECT_ROOT DATABRICKS_HOST
export LAKEBASE_MODE ENDPOINT_NAME

python3 << 'PYTHON_EOF'
import os
import sys
import re
import glob

import warnings
warnings.filterwarnings('ignore')

HOST = os.environ.get('LAKEBASE_HOST', '')
DATABASE = os.environ.get('LAKEBASE_DATABASE', '')
SCHEMA = os.environ.get('LAKEBASE_SCHEMA', '')
PORT = int(os.environ.get('LAKEBASE_PORT', '5432'))
USER = os.environ.get('LAKEBASE_USER', '')
ACTION = os.environ.get('ACTION', 'create')
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', '.')
LAKEBASE_MODE = os.environ.get('LAKEBASE_MODE', 'provisioned')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME', '')

# Paths to SQL files
DDL_DIR = os.path.join(PROJECT_ROOT, 'db', 'lakebase', 'ddl')
DML_SEED_DIR = os.path.join(PROJECT_ROOT, 'db', 'lakebase', 'dml_seed')

print(f"Action: {ACTION}")
print()

# =============================================================================
# SQL File Processing Functions
# =============================================================================

def transform_sql_for_postgres(sql_content: str, schema: str) -> str:
    """
    Transform SQL from Spark/Databricks syntax to PostgreSQL syntax.
    
    Transformations:
    - ${catalog}.${schema}. -> schema.
    - ${schema}. -> schema.
    - current_timestamp() -> CURRENT_TIMESTAMP
    - current_user() -> CURRENT_USER
    """
    # Replace catalog.schema with just schema
    sql_content = re.sub(r'\$\{catalog\}\.\$\{schema\}\.', f'{schema}.', sql_content)
    # Replace ${schema} with actual schema
    sql_content = sql_content.replace('${schema}', schema)
    # Replace Spark functions with PostgreSQL equivalents
    sql_content = sql_content.replace('current_timestamp()', 'CURRENT_TIMESTAMP')
    sql_content = sql_content.replace('current_user()', 'CURRENT_USER')
    
    return sql_content


def read_sql_file(file_path: str, schema: str) -> str:
    """Read SQL file and apply transformations."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return transform_sql_for_postgres(content, schema)


def parse_sql_statements(sql_content: str) -> list:
    """
    Parse SQL content into individual statements.
    Handles multi-line INSERT statements with complex string values.
    Uses character-by-character parsing to properly handle embedded quotes.
    """
    statements = []
    current_stmt = []
    i = 0
    content_len = len(sql_content)
    
    while i < content_len:
        # Check for comment at start of line or after statement boundary
        if sql_content[i:i+2] == '--':
            # Skip to end of line
            while i < content_len and sql_content[i] != '\n':
                i += 1
            i += 1  # Skip the newline
            continue
        
        # Skip whitespace at statement boundaries
        if not current_stmt and sql_content[i] in ' \t\n\r':
            i += 1
            continue
        
        # Start of a new statement
        stmt_start = i
        in_string = False
        paren_depth = 0
        
        # Process until we find the end of the statement
        while i < content_len:
            char = sql_content[i]
            
            # Handle string literals
            if char == "'" and not in_string:
                in_string = True
                i += 1
                continue
            elif char == "'" and in_string:
                # Check for escaped quote ('')
                if i + 1 < content_len and sql_content[i + 1] == "'":
                    i += 2  # Skip both quotes
                    continue
                in_string = False
                i += 1
                continue
            
            if in_string:
                i += 1
                continue
            
            # Handle comments outside strings
            if char == '-' and i + 1 < content_len and sql_content[i + 1] == '-':
                # Skip to end of line
                while i < content_len and sql_content[i] != '\n':
                    i += 1
                i += 1
                continue
            
            # Track parentheses
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            
            # Statement end: semicolon outside string and balanced parens
            if char == ';' and not in_string and paren_depth <= 0:
                stmt = sql_content[stmt_start:i+1].strip()
                if stmt and not stmt.startswith('--'):
                    statements.append(stmt)
                i += 1
                break
            
            i += 1
        else:
            # Reached end without semicolon
            stmt = sql_content[stmt_start:].strip()
            if stmt and not stmt.startswith('--'):
                # Try to salvage incomplete statement
                if 'INSERT' in stmt.upper() or 'CREATE' in stmt.upper():
                    statements.append(stmt)
            break
    
    return statements


def execute_sql_file(cursor, file_path: str, schema: str, ignore_errors: bool = False) -> int:
    """Execute all statements from a SQL file."""
    sql_content = read_sql_file(file_path, schema)
    statements = parse_sql_statements(sql_content)
    
    executed = 0
    for stmt in statements:
        try:
            cursor.execute(stmt)
            executed += 1
        except Exception as e:
            error_msg = str(e).lower()
            # Ignore duplicate key and already exists errors
            if 'duplicate key' in error_msg or 'already exists' in error_msg:
                continue
            elif ignore_errors:
                continue
            else:
                print(f"      Warning: {str(e)[:80]}")
    
    return executed


def get_ddl_files() -> list:
    """Get sorted list of DDL SQL files (excluding UC-only files like tags)."""
    if not os.path.exists(DDL_DIR):
        return []
    EXCLUDE_PATTERNS = {'apply_tags'}
    files = sorted(glob.glob(os.path.join(DDL_DIR, '*.sql')))
    return [f for f in files if not any(p in os.path.basename(f) for p in EXCLUDE_PATTERNS)]


def get_dml_seed_files() -> list:
    """Get sorted list of DML seed SQL files."""
    if not os.path.exists(DML_SEED_DIR):
        return []
    files = sorted(glob.glob(os.path.join(DML_SEED_DIR, '*.sql')))
    return files


# =============================================================================
# Database Connection
# =============================================================================

# Get OAuth token (or autoscaling credential)
try:
    from databricks.sdk import WorkspaceClient
    db_host = os.environ.get('DATABRICKS_HOST', '')
    w = WorkspaceClient(host=db_host) if db_host else WorkspaceClient()

    token = None
    if LAKEBASE_MODE == 'autoscaling' and ENDPOINT_NAME:
        credential = w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)
        token = credential.token
        if not USER:
            USER = w.current_user.me().user_name
        print(f"✓ Got Autoscaling database credential (user={USER})")
    else:
        if hasattr(w.config, 'token') and w.config.token:
            token = w.config.token
        else:
            headers = w.config.authenticate()
            if headers and 'Authorization' in headers:
                auth = headers['Authorization']
                if auth.startswith('Bearer '):
                    token = auth[7:]
        if token:
            print("✓ Got OAuth token")

    if not token:
        print("❌ Failed to get authentication token")
        sys.exit(1)
    print()
except Exception as e:
    print(f"❌ Error getting token: {e}")
    sys.exit(1)

# Connect to Lakebase (with retry for fresh instances / scale-to-zero cold starts)
import time as _time

# Prefer psycopg3, fall back to psycopg2
try:
    import psycopg as _pg
    _USE_PSYCOPG3 = True
except ImportError:
    import psycopg2 as _pg
    _USE_PSYCOPG3 = False

MAX_RETRIES = 5
RETRY_DELAY = 10

conn = None
for attempt in range(1, MAX_RETRIES + 1):
    try:
        if _USE_PSYCOPG3:
            conn = _pg.connect(
                host=HOST, port=PORT, dbname=DATABASE,
                user=USER, password=token, sslmode='require',
                autocommit=True,
            )
        else:
            conn = _pg.connect(
                host=HOST, port=PORT, database=DATABASE,
                user=USER, password=token, sslmode='require',
            )
            conn.autocommit = True
        cursor = conn.cursor()
        print("✓ Connected to Lakebase")
        print()
        break
    except Exception as e:
        if attempt == MAX_RETRIES:
            print(f"❌ Failed to connect to Lakebase after {MAX_RETRIES} attempts: {e}")
            sys.exit(1)
        wait = RETRY_DELAY * attempt
        print(f"⏳ Connection attempt {attempt}/{MAX_RETRIES} failed, retrying in {wait}s...")
        print(f"   ({e})")
        _time.sleep(wait)

# =============================================================================
# Execute Actions
# =============================================================================

try:
    if ACTION == "status":
        print("Checking table status...")
        
        cursor.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='{SCHEMA}' AND table_type='BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            print("  No tables found in schema.")
        for table in tables:
            cursor.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema='{SCHEMA}' AND table_name='{table}'
            """)
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: ✓ exists ({count} rows)")
            else:
                print(f"  {table}: ✗ not found")
    
    elif ACTION == "drop":
        print("Dropping tables...")
        cursor.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='{SCHEMA}' AND table_type='BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{table} CASCADE")
            print(f"  Dropped {table}")
        print("✓ Tables dropped")
    
    elif ACTION == "recreate":
        print("Recreating tables...")
        print()
        
        # Drop existing tables (discover dynamically)
        print("  Dropping existing tables...")
        cursor.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='{SCHEMA}' AND table_type='BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{table} CASCADE")
        
        # Create schema
        print("  Creating schema...")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        
        # Execute DDL files
        print(f"  Executing DDL from {DDL_DIR}/...")
        ddl_files = get_ddl_files()
        for ddl_file in ddl_files:
            filename = os.path.basename(ddl_file)
            print(f"    {filename}...", end=" ")
            count = execute_sql_file(cursor, ddl_file, SCHEMA, ignore_errors=True)
            print(f"({count} statements)")
        
        # Execute DML seed files
        print(f"  Executing DML seed from {DML_SEED_DIR}/...")
        dml_files = get_dml_seed_files()
        for dml_file in dml_files:
            filename = os.path.basename(dml_file)
            print(f"    {filename}...", end=" ")
            count = execute_sql_file(cursor, dml_file, SCHEMA, ignore_errors=True)
            print(f"({count} statements)")
        
        # Reset all sequences in the schema to avoid duplicate key errors
        print("  Resetting sequences...")
        try:
            cursor.execute(f"""
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_schema = '{SCHEMA}'
            """)
            seqs = [row[0] for row in cursor.fetchall()]
            for seq_name in seqs:
                parts = seq_name.rsplit('_', 1)
                if len(parts) == 2 and parts[1] == 'seq':
                    col_and_table = parts[0]
                else:
                    continue
                tbl_col = col_and_table.rsplit('_', 1)
                if len(tbl_col) == 2:
                    tbl, col = tbl_col
                    try:
                        cursor.execute(f"SELECT MAX({col}) FROM {SCHEMA}.{tbl}")
                        max_val = cursor.fetchone()[0] or 0
                        cursor.execute(f"SELECT setval('{SCHEMA}.{seq_name}', {max_val + 1}, false)")
                        print(f"    {seq_name} reset to {max_val + 1}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"    (sequence reset skipped: {e})")
        
        print()
        print("✓ Tables recreated and seeded successfully")
    
    elif ACTION == "create":
        print("Creating tables (if not exist)...")
        print()
        
        # Create schema
        print("  Creating schema...")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        
        # Execute DDL files
        print(f"  Executing DDL from {DDL_DIR}/...")
        ddl_files = get_ddl_files()
        for ddl_file in ddl_files:
            filename = os.path.basename(ddl_file)
            print(f"    {filename}...", end=" ")
            count = execute_sql_file(cursor, ddl_file, SCHEMA, ignore_errors=True)
            print(f"({count} statements)")
        
        # Check if tables need seeding by checking row count of first table found
        needs_seed = True
        try:
            cursor.execute(f"""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='{SCHEMA}' AND table_type='BASE TABLE'
                ORDER BY table_name LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{row[0]}")
                total = cursor.fetchone()[0] or 0
                needs_seed = total == 0
        except Exception:
            pass
        
        if needs_seed:
            print(f"  Executing DML seed from {DML_SEED_DIR}/...")
            dml_files = get_dml_seed_files()
            for dml_file in dml_files:
                filename = os.path.basename(dml_file)
                print(f"    {filename}...", end=" ")
                count = execute_sql_file(cursor, dml_file, SCHEMA, ignore_errors=True)
                print(f"({count} statements)")
            
            print("  Resetting sequences...")
            try:
                cursor.execute(f"""
                    SELECT sequence_name FROM information_schema.sequences
                    WHERE sequence_schema = '{SCHEMA}'
                """)
                for (seq_name,) in cursor.fetchall():
                    try:
                        parts = seq_name.rsplit('_', 1)
                        if len(parts) == 2 and parts[1] == 'seq':
                            tbl_col = parts[0].rsplit('_', 1)
                            if len(tbl_col) == 2:
                                tbl, col = tbl_col
                                cursor.execute(f"SELECT MAX({col}) FROM {SCHEMA}.{tbl}")
                                max_val = cursor.fetchone()[0] or 0
                                cursor.execute(f"SELECT setval('{SCHEMA}.{seq_name}', {max_val + 1}, false)")
                    except Exception:
                        pass
            except Exception:
                pass
        else:
            print(f"  Tables already have data, skipping seed.")
        
        print()
        print("✓ Tables ready")

    # ── Create Postgres roles for the app service principal ──
    # databricks_auth extension + databricks_create_role() are autoscaling-only SQL functions.
    # For provisioned, SP roles are managed via REST API in deploy.sh (Step 3b).
    sp_id = os.environ.get("APP_SERVICE_PRINCIPAL_ID", "")
    lakebase_mode = os.environ.get("LAKEBASE_MODE", "provisioned")
    if sp_id and lakebase_mode == "autoscaling":
        print()
        print("Setting up Postgres roles for app service principal...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
            print(f"  ✓ databricks_auth extension ready")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ✓ databricks_auth extension already exists")
            else:
                print(f"  ⚠ Could not create extension: {e}")

        try:
            cursor.execute(f"SELECT databricks_create_role('{sp_id}', 'SERVICE_PRINCIPAL')")
            print(f"  ✓ Postgres role created for SP: {sp_id[:20]}...")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ✓ Postgres role already exists for SP: {sp_id[:20]}...")
            else:
                print(f"  ⚠ Could not create SP role: {e}")

        try:
            cursor.execute(f'GRANT USAGE ON SCHEMA {SCHEMA} TO "{sp_id}"')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO "{sp_id}"')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{sp_id}"')
            print(f"  ✓ Schema permissions granted to SP on {SCHEMA}")
        except Exception as e:
            print(f"  ⚠ Could not grant schema permissions: {e}")

        conn.commit()
        print("✓ Service principal database access configured")

    # ── Grant public role access so all authenticated users can use the workshop ──
    print()
    print("Setting up public access for all workspace users...")
    try:
        cursor.execute(f"GRANT CREATE ON DATABASE {DATABASE} TO public")
        print(f"  ✓ CREATE on database {DATABASE} granted to public")
    except Exception as e:
        if "already" in str(e).lower():
            print("  ✓ CREATE on database already granted to public")
        else:
            print(f"  ⚠ Could not grant CREATE on database: {e}")

    try:
        cursor.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO public")
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO public")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO public")
        print(f"  ✓ Schema and table permissions granted to public on {SCHEMA}")
    except Exception as e:
        print(f"  ⚠ Could not grant public schema permissions: {e}")

    conn.commit()
    print("✓ Public access configured for all authenticated users")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    cursor.close()
    conn.close()

print()
print("Done!")
PYTHON_EOF

echo ""
echo -e "${GREEN}✓ Lakebase setup complete${NC}"

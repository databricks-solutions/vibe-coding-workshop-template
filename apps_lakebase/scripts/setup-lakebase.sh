#!/bin/bash
# =============================================================================
# Vibe Coding Workshop - Lakebase Table Setup
# =============================================================================
#
# Creates or recreates the tables in Lakebase using Python/psycopg2.
# Optionally creates the Lakebase instance if it doesn't exist.
# Reads DDL from db/lakehouse/ddl/*.sql
# Reads DML seed data from db/lakehouse/dml_seed/*.sql
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
#   - Python with psycopg2-binary, requests
#   - databricks CLI (authenticated)
#
# SQL FILES:
#   db/lakehouse/ddl/           - Table definitions (PostgreSQL syntax)
#   db/lakehouse/dml_seed/      - Seed data (will be transformed from Spark to PG)
#
# CONFIGURATION (environment variables):
#   DATABRICKS_HOST             - Workspace URL (default from app.yaml)
#   LAKEBASE_INSTANCE_NAME      - Instance name (default: vibe-coding-workshop-lakebase)
#   APP_NAME                    - App name (default: vibe-coding-workshop-app)
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
DATABRICKS_HOST="${DATABRICKS_HOST:-https://e2-demo-field-eng.cloud.databricks.com}"

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
LAKEBASE_USER="${LAKEBASE_USER_OVERRIDE:-$(get_yaml_value "LAKEBASE_USER")}"

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
echo ""

# SAFETY CHECK: Confirm if targeting production schema
if [[ "$LAKEBASE_SCHEMA" == "vibe_coding_workshop" && "$ACTION" == "recreate" ]]; then
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ⚠️  WARNING: You are about to RECREATE tables in PRODUCTION!${NC}"
    echo -e "${RED}  Schema: $LAKEBASE_SCHEMA${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    read -p "Type 'YES-PRODUCTION' to confirm: " confirmation
    if [[ "$confirmation" != "YES-PRODUCTION" ]]; then
        echo -e "${RED}Aborted. Use --target development for dev environment.${NC}"
        exit 1
    fi
fi

# =============================================================================
# Check prerequisites
# =============================================================================

if ! databricks current-user me &>/dev/null; then
    echo -e "${RED}Error: Not authenticated to Databricks${NC}"
    echo "Run: databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com"
    exit 1
fi

# Check if required Python packages are available
python3 -c "import psycopg2" 2>/dev/null || {
    echo -e "${YELLOW}Installing psycopg2-binary...${NC}"
    pip3 install -q psycopg2-binary
}

python3 -c "import requests" 2>/dev/null || {
    echo -e "${YELLOW}Installing requests...${NC}"
    pip3 install -q requests
}

# =============================================================================
# Run Python script for database operations
# =============================================================================

# Export variables for Python
export LAKEBASE_HOST LAKEBASE_DATABASE LAKEBASE_SCHEMA LAKEBASE_PORT LAKEBASE_USER ACTION PROJECT_ROOT

python3 << 'PYTHON_EOF'
import os
import sys
import re
import glob

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

# Configuration from environment
HOST = os.environ.get('LAKEBASE_HOST', '')
DATABASE = os.environ.get('LAKEBASE_DATABASE', '')
SCHEMA = os.environ.get('LAKEBASE_SCHEMA', '')
PORT = int(os.environ.get('LAKEBASE_PORT', '5432'))
USER = os.environ.get('LAKEBASE_USER', '')
ACTION = os.environ.get('ACTION', 'create')
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', '.')

# Paths to SQL files
DDL_DIR = os.path.join(PROJECT_ROOT, 'db', 'lakehouse', 'ddl')
DML_SEED_DIR = os.path.join(PROJECT_ROOT, 'db', 'lakehouse', 'dml_seed')

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
    """Get sorted list of DDL SQL files."""
    if not os.path.exists(DDL_DIR):
        return []
    files = sorted(glob.glob(os.path.join(DDL_DIR, '*.sql')))
    return files


def get_dml_seed_files() -> list:
    """Get sorted list of DML seed SQL files."""
    if not os.path.exists(DML_SEED_DIR):
        return []
    files = sorted(glob.glob(os.path.join(DML_SEED_DIR, '*.sql')))
    return files


# =============================================================================
# Database Connection
# =============================================================================

# Get OAuth token
try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient(host="https://e2-demo-field-eng.cloud.databricks.com")
    
    token = None
    if hasattr(w.config, 'token') and w.config.token:
        token = w.config.token
    else:
        headers = w.config.authenticate()
        if headers and 'Authorization' in headers:
            auth = headers['Authorization']
            if auth.startswith('Bearer '):
                token = auth[7:]
    
    if not token:
        print("❌ Failed to get OAuth token")
        sys.exit(1)
    
    print("✓ Got OAuth token")
    print()
except Exception as e:
    print(f"❌ Error getting OAuth token: {e}")
    sys.exit(1)

# Connect to Lakebase
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=token,
        sslmode='require'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    print("✓ Connected to Lakebase")
    print()
except Exception as e:
    print(f"❌ Failed to connect to Lakebase: {e}")
    sys.exit(1)

# =============================================================================
# Execute Actions
# =============================================================================

try:
    if ACTION == "status":
        print("Checking table status...")
        
        tables = ['usecase_descriptions', 'section_input_prompts', 'sessions']
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
        tables = ['usecase_descriptions', 'section_input_prompts', 'sessions']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{table}")
            print(f"  Dropped {table}")
        print("✓ Tables dropped")
    
    elif ACTION == "recreate":
        print("Recreating tables...")
        print()
        
        # Drop existing tables
        print("  Dropping existing tables...")
        tables = ['usecase_descriptions', 'section_input_prompts', 'sessions']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{table}")
        
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
        
        # Reset sequences after seeding to avoid duplicate key errors
        print("  Resetting sequences...")
        for table, col in [('usecase_descriptions', 'config_id'), ('section_input_prompts', 'input_id')]:
            try:
                cursor.execute(f"SELECT MAX({col}) FROM {SCHEMA}.{table}")
                max_val = cursor.fetchone()[0] or 0
                seq_name = f"{SCHEMA}.{table}_{col}_seq"
                cursor.execute(f"SELECT setval('{seq_name}', {max_val + 1}, false)")
                print(f"    {table}.{col} sequence reset to {max_val + 1}")
            except Exception as e:
                print(f"    (sequence for {table}.{col} not found or already correct)")
        
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
        
        # Check if tables need seeding
        cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.usecase_descriptions")
        uc_count = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.section_input_prompts")
        sip_count = cursor.fetchone()[0]
        
        if uc_count == 0 or sip_count == 0:
            print(f"  Executing DML seed from {DML_SEED_DIR}/...")
            dml_files = get_dml_seed_files()
            for dml_file in dml_files:
                filename = os.path.basename(dml_file)
                print(f"    {filename}...", end=" ")
                count = execute_sql_file(cursor, dml_file, SCHEMA, ignore_errors=True)
                print(f"({count} statements)")
            
            # Reset sequences after seeding to avoid duplicate key errors
            print("  Resetting sequences...")
            for table, col in [('usecase_descriptions', 'config_id'), ('section_input_prompts', 'input_id')]:
                try:
                    cursor.execute(f"SELECT MAX({col}) FROM {SCHEMA}.{table}")
                    max_val = cursor.fetchone()[0] or 0
                    seq_name = f"{SCHEMA}.{table}_{col}_seq"
                    cursor.execute(f"SELECT setval('{seq_name}', {max_val + 1}, false)")
                    print(f"    {table}.{col} sequence reset to {max_val + 1}")
                except Exception as e:
                    print(f"    (sequence for {table}.{col} not found or already correct)")
        else:
            print(f"  Tables already have data (usecase: {uc_count}, section_prompts: {sip_count})")
        
        print()
        print("✓ Tables ready")

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
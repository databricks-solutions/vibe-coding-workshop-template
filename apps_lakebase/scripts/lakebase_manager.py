#!/usr/bin/env python3
"""
Lakebase Instance Manager
=========================
Manages Lakebase PostgreSQL instances and permissions for Databricks Apps.
Supports both Autoscaling (preferred) and Provisioned (legacy) Lakebase tiers.

This script automates the setup of Lakebase access for Databricks Apps, including:
  - Checking Lakebase connectivity and status
  - Getting app service principal information
  - Granting Unity Catalog permissions
  - Adding Lakebase database roles (DATABRICKS_SUPERUSER)
  - Listing existing Lakebase roles

LAKEBASE TIERS:
  Autoscaling: Uses ENDPOINT_NAME (projects/.../branches/.../endpoints/...)
               Credential via WorkspaceClient().postgres.generate_database_credential()
  Provisioned: Uses instance name (flat)
               Credential via OAuth token or database.generate_database_credential()

DATABRICKS APIS USED:
  - GET   /api/2.0/apps/{app_name}                    -> Get app details + service principal
  - PATCH /api/2.0/apps/{app_name}                    -> Update app (e.g., add resources)
  - GET   /api/2.0/database/instances/{instance}      -> Get Lakebase instance details (provisioned)
  - GET   /api/2.0/database/instances/{instance}/roles -> List database roles (provisioned)
  - POST  /api/2.0/database/instances/{instance}/roles -> Add database role (provisioned)
  - PATCH /api/2.1/unity-catalog/permissions/catalog/{catalog} -> Grant catalog permissions

Usage:
    python scripts/lakebase_manager.py --action check               # Check connectivity
    python scripts/lakebase_manager.py --action app-info            # Get app service principal
    python scripts/lakebase_manager.py --action full-info           # Get full app details
    python scripts/lakebase_manager.py --action status              # Full status check
    python scripts/lakebase_manager.py --action grant-permissions   # Grant catalog permissions
    python scripts/lakebase_manager.py --action add-lakebase-role   # Add database role
    python scripts/lakebase_manager.py --action list-lakebase-roles # List database roles
    python scripts/lakebase_manager.py --action link-app-resource   # Link Lakebase to app (App Resources)
    python scripts/lakebase_manager.py --action instructions        # Print setup instructions

Configuration:
    Set environment variables or use defaults from app.yaml:
    - DATABRICKS_HOST: Workspace URL
    - LAKEBASE_INSTANCE_NAME: Lakebase instance name
    - APP_NAME: Databricks App name
    - LAKEBASE_MODE: "autoscaling" or "provisioned" (auto-detected from ENDPOINT_NAME)
    - ENDPOINT_NAME: Autoscaling endpoint path (from app.yaml)
"""

import os
import sys
import json
import argparse
import subprocess
import re
import time
from typing import Optional, Dict, Any, Tuple

try:
    import requests
except ImportError:
    print("Missing required package: requests")
    print("   Install with: pip install requests")
    sys.exit(1)

# Prefer psycopg3, fall back to psycopg2
try:
    import psycopg as _pg
    _USE_PSYCOPG3 = True
except ImportError:
    try:
        import psycopg2 as _pg
        _USE_PSYCOPG3 = False
    except ImportError:
        print("Missing required package: psycopg or psycopg2")
        print("   Install with: pip install 'psycopg[binary]' or pip install psycopg2-binary")
        sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration for Lakebase management."""

    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")

    LAKEBASE_HOST = None
    LAKEBASE_DATABASE = None
    LAKEBASE_SCHEMA = None
    LAKEBASE_PORT = 5432
    LAKEBASE_USER = None
    LAKEBASE_INSTANCE_NAME = os.getenv("LAKEBASE_INSTANCE_NAME", "")

    # Autoscaling-specific
    ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "")
    LAKEBASE_MODE = os.getenv("LAKEBASE_MODE", "")

    APP_NAME = os.getenv("APP_NAME", "")

    @classmethod
    def load_from_app_yaml(cls, project_root: str = "."):
        """Load configuration from app.yaml."""
        app_yaml_path = os.path.join(project_root, "app.yaml")

        if not os.path.exists(app_yaml_path):
            print(f"  app.yaml not found at {app_yaml_path}")
            return

        with open(app_yaml_path, 'r') as f:
            content = f.read()

        def get_yaml_value(key):
            match = re.search(rf'name: {key}.*?value:\s*"([^"]*)"', content, re.DOTALL)
            return match.group(1) if match else None

        cls.LAKEBASE_HOST = cls.LAKEBASE_HOST or get_yaml_value('LAKEBASE_HOST')
        cls.LAKEBASE_DATABASE = cls.LAKEBASE_DATABASE or get_yaml_value('LAKEBASE_DATABASE')
        cls.LAKEBASE_SCHEMA = cls.LAKEBASE_SCHEMA or get_yaml_value('LAKEBASE_SCHEMA')
        cls.LAKEBASE_PORT = cls.LAKEBASE_PORT or int(get_yaml_value('LAKEBASE_PORT') or '5432')
        cls.LAKEBASE_USER = cls.LAKEBASE_USER or get_yaml_value('LAKEBASE_USER')
        cls.ENDPOINT_NAME = cls.ENDPOINT_NAME or get_yaml_value('ENDPOINT_NAME') or ""

        # Auto-detect mode from ENDPOINT_NAME format
        if not cls.LAKEBASE_MODE:
            if cls.ENDPOINT_NAME.startswith("projects/"):
                cls.LAKEBASE_MODE = "autoscaling"
            else:
                cls.LAKEBASE_MODE = "provisioned"

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            "databricks_host": cls.DATABRICKS_HOST,
            "lakebase_host": cls.LAKEBASE_HOST,
            "lakebase_database": cls.LAKEBASE_DATABASE,
            "lakebase_schema": cls.LAKEBASE_SCHEMA,
            "lakebase_port": cls.LAKEBASE_PORT,
            "lakebase_user": cls.LAKEBASE_USER,
            "lakebase_instance_name": cls.LAKEBASE_INSTANCE_NAME,
            "lakebase_mode": cls.LAKEBASE_MODE,
            "endpoint_name": cls.ENDPOINT_NAME,
            "app_name": cls.APP_NAME,
        }


# =============================================================================
# HELPERS
# =============================================================================

MAX_RETRIES = 5
RETRY_DELAY = 10


def _get_workspace_client(host: str):
    """Get a Databricks WorkspaceClient (lazy import to avoid hard dependency)."""
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient(host=host) if host else WorkspaceClient()


def get_databricks_token(host: str) -> Optional[str]:
    """Get OAuth token from Databricks CLI."""
    if not host:
        print("DATABRICKS_HOST is not set.")
        print("   Set it via --host, DATABRICKS_HOST env var, or app.yaml")
        return None
    try:
        result = subprocess.run(
            ['databricks', 'auth', 'token', '--host', host],
            capture_output=True, text=True, check=True
        )
        token_data = json.loads(result.stdout)
        return token_data.get('access_token')
    except Exception as e:
        print(f"Failed to get auth token: {e}")
        print(f"   Run: databricks auth login --host {host}")
        return None


def get_lakebase_db_token(config) -> Optional[str]:
    """
    Get a database credential appropriate for the Lakebase mode.
    Autoscaling: uses WorkspaceClient().postgres.generate_database_credential()
    Provisioned: uses OAuth token from CLI
    """
    if config.LAKEBASE_MODE == "autoscaling" and config.ENDPOINT_NAME:
        try:
            w = _get_workspace_client(config.DATABRICKS_HOST)
            credential = w.postgres.generate_database_credential(endpoint=config.ENDPOINT_NAME)
            if not config.LAKEBASE_USER:
                config.LAKEBASE_USER = w.current_user.me().user_name
            return credential.token
        except Exception as e:
            print(f"  Autoscaling credential failed ({e}), falling back to OAuth token")

    return get_databricks_token(config.DATABRICKS_HOST)


def _api_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_full_app_info(host: str, token: str, app_name: str) -> Optional[Dict[str, Any]]:
    """Get full app information including URL, status, and service principal."""
    try:
        response = requests.get(f"{host}/api/2.0/apps/{app_name}", headers=_api_headers(token))
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Could not get app info: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Error getting app info: {e}")
        return None


def get_app_service_principal(host: str, token: str, app_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Get the app's service principal ID and name."""
    app_info = get_full_app_info(host, token, app_name)
    if app_info:
        return (
            app_info.get('service_principal_client_id'),
            app_info.get('service_principal_name')
        )
    return None, None


def grant_catalog_permissions(host: str, token: str, catalog_name: str, principal_id: str) -> bool:
    """Grant ALL_PRIVILEGES on a catalog to a service principal."""
    payload = {
        "changes": [{"principal": principal_id, "add": ["ALL_PRIVILEGES"]}]
    }
    try:
        response = requests.patch(
            f"{host}/api/2.1/unity-catalog/permissions/catalog/{catalog_name}",
            headers=_api_headers(token), json=payload
        )
        if response.status_code == 200:
            return True
        print(f"  Permission grant returned: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    except Exception as e:
        print(f"  Error granting permissions: {e}")
        return False


def deploy_app_source(host: str, token: str, app_name: str, source_path: str) -> bool:
    """Deploy source code to a Databricks App."""
    try:
        response = requests.post(
            f"{host}/api/2.0/apps/{app_name}/deployments",
            headers=_api_headers(token), json={"source_code_path": source_path}
        )
        if response.status_code in [200, 201]:
            result = response.json()
            status = result.get('status', {}).get('state', 'UNKNOWN')
            print(f"   Deployment status: {status}")
            return True
        print(f"  Deployment returned: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    except Exception as e:
        print(f"  Error deploying app: {e}")
        return False


def add_lakebase_role(host: str, token: str, instance_name: str, principal_id: str,
                      identity_type: str = "SERVICE_PRINCIPAL",
                      membership_role: str = "DATABRICKS_SUPERUSER") -> bool:
    """Add a database role to a Lakebase instance (provisioned API)."""
    payload = {
        "name": principal_id,
        "identity_type": identity_type,
        "membership_role": membership_role
    }
    try:
        response = requests.post(
            f"{host}/api/2.0/database/instances/{instance_name}/roles",
            headers=_api_headers(token), json=payload
        )
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   Role: {result.get('membership_role')}")
            print(f"   Identity Type: {result.get('identity_type')}")
            return True
        elif response.status_code == 409:
            print(f"  Role already exists")
            return True
        print(f"  Add role returned: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    except Exception as e:
        print(f"  Error adding role: {e}")
        return False


def get_lakebase_roles(host: str, token: str, instance_name: str) -> list:
    """Get all database roles for a Lakebase instance (provisioned API)."""
    try:
        response = requests.get(
            f"{host}/api/2.0/database/instances/{instance_name}/roles",
            headers=_api_headers(token)
        )
        if response.status_code == 200:
            return response.json().get('database_instance_roles', [])
        print(f"  Get roles returned: {response.status_code}")
        return []
    except Exception as e:
        print(f"  Error getting roles: {e}")
        return []


def get_app_resources(host: str, token: str, app_name: str) -> list:
    """Get existing app resources for a Databricks App."""
    app_info = get_full_app_info(host, token, app_name)
    if app_info:
        return app_info.get('resources', [])
    return []


def link_app_resource(host: str, token: str, app_name: str, instance_name: str,
                      database_name: str = "databricks_postgres",
                      permission: str = "CAN_CONNECT_AND_CREATE") -> bool:
    """
    Link a Lakebase instance to a Databricks App as an App Resource.
    Enables automatic PGPASSWORD injection at runtime.
    """
    payload = {
        "resources": [{
            "name": "database",
            "database": {
                "instance_name": instance_name,
                "database_name": database_name,
                "permission": permission
            }
        }]
    }
    try:
        response = requests.patch(
            f"{host}/api/2.0/apps/{app_name}",
            headers=_api_headers(token), json=payload
        )
        if response.status_code == 200:
            result = response.json()
            resources = result.get('resources', [])
            for r in resources:
                db = r.get('database', {})
                if db.get('instance_name') == instance_name:
                    print(f"   Instance: {db.get('instance_name')}")
                    print(f"   Database: {db.get('database_name')}")
                    print(f"   Permission: {db.get('permission')}")
                    return True
            return True
        print(f"  Link app resource returned: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    except Exception as e:
        print(f"  Error linking app resource: {e}")
        return False


def check_lakebase_connection(config, token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Check Lakebase connectivity with retry and return table counts.
    Discovers tables dynamically from information_schema.
    """
    if not config.LAKEBASE_HOST:
        return False, {"error": "LAKEBASE_HOST not configured"}

    user = config.LAKEBASE_USER
    if not user:
        try:
            result = subprocess.run(
                ['databricks', 'current-user', 'me', '--output', 'json'],
                capture_output=True, text=True, check=True
            )
            user = json.loads(result.stdout).get('userName', '')
        except Exception:
            return False, {"error": "Could not determine current user for DB connection"}

    conn = None
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if _USE_PSYCOPG3:
                conn = _pg.connect(
                    host=config.LAKEBASE_HOST, port=config.LAKEBASE_PORT,
                    dbname=config.LAKEBASE_DATABASE, user=user,
                    password=token, sslmode='require', autocommit=True,
                )
            else:
                conn = _pg.connect(
                    host=config.LAKEBASE_HOST, port=config.LAKEBASE_PORT,
                    database=config.LAKEBASE_DATABASE, user=user,
                    password=token, sslmode='require',
                )
                conn.autocommit = True
            break
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"  Connection attempt {attempt}/{MAX_RETRIES} failed, retrying in {wait}s...")
                time.sleep(wait)

    if conn is None:
        return False, {"error": str(last_err)}

    try:
        cursor = conn.cursor()
        # Discover tables dynamically
        cursor.execute(f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='{config.LAKEBASE_SCHEMA}' AND table_type='BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            cursor.close()
            conn.close()
            return True, {"_info": "No tables found in schema"}

        counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {config.LAKEBASE_SCHEMA}.{table}")
                counts[table] = cursor.fetchone()[0]
            except Exception as e:
                counts[table] = f"ERROR: {e}"

        cursor.close()
        conn.close()
        return True, counts
    except Exception as e:
        if conn:
            conn.close()
        return False, {"error": str(e)}


# =============================================================================
# ACTIONS
# =============================================================================

def action_check(config) -> int:
    """Check Lakebase connectivity."""
    print("Checking Lakebase Connection\n")

    db_token = get_lakebase_db_token(config)
    if not db_token:
        return 1

    print(f"Configuration:")
    print(f"  Host:     {(config.LAKEBASE_HOST or 'NOT SET')[:50]}...")
    print(f"  Database: {config.LAKEBASE_DATABASE or 'NOT SET'}")
    print(f"  Schema:   {config.LAKEBASE_SCHEMA or 'NOT SET'}")
    print(f"  Port:     {config.LAKEBASE_PORT}")
    print(f"  User:     {config.LAKEBASE_USER or '(auto-detect)'}")
    print(f"  Mode:     {config.LAKEBASE_MODE}")
    print()

    success, counts = check_lakebase_connection(config, db_token)

    if success:
        print("Connection successful!\n")
        if "_info" in counts:
            print(f"  {counts['_info']}")
        else:
            print("Table counts:")
            for table, count in counts.items():
                print(f"  {table}: {count} rows")
        return 0
    else:
        print(f"Connection failed: {counts.get('error', 'Unknown error')}")
        return 1


def action_app_info(config) -> int:
    """Get app service principal information."""
    print("Getting App Service Principal Info\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    sp_id, sp_name = get_app_service_principal(config.DATABRICKS_HOST, token, config.APP_NAME)

    if sp_id:
        print(f"  App Name: {config.APP_NAME}")
        print(f"  Service Principal ID: {sp_id}")
        print(f"  Service Principal Name: {sp_name}")
        return 0
    else:
        print(f"  Could not get service principal for app: {config.APP_NAME}")
        print("   Is the app deployed?")
        return 1


def action_status(config) -> int:
    """Full status check."""
    print("=" * 60)
    print("LAKEBASE STATUS CHECK")
    print("=" * 60)
    print()

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    print("1. App Information:")
    sp_id, sp_name = get_app_service_principal(config.DATABRICKS_HOST, token, config.APP_NAME)
    if sp_id:
        print(f"   App Name: {config.APP_NAME}")
        print(f"   Service Principal ID: {sp_id}")
        print(f"   Service Principal Name: {sp_name}")
    else:
        print(f"   Could not get app info")
        sp_id = "UNKNOWN"

    print(f"\n2. Lakebase Connection:")
    print(f"   Instance: {config.LAKEBASE_INSTANCE_NAME}")
    print(f"   Mode: {config.LAKEBASE_MODE}")
    print(f"   Host: {(config.LAKEBASE_HOST or 'NOT SET')[:50]}...")

    db_token = get_lakebase_db_token(config)
    if db_token:
        success, counts = check_lakebase_connection(config, db_token)
        if success:
            print("   Connection successful!")
            for table, count in counts.items():
                if not table.startswith("_"):
                    print(f"     {table}: {count} rows")
        else:
            print(f"   Connection failed: {counts.get('error', 'Unknown')}")
    else:
        print("   Could not obtain database credential")
        success = False

    print("\n" + "=" * 60)
    print("PERMISSION SETUP (if needed)")
    print("=" * 60)
    host_display = config.DATABRICKS_HOST.replace('https://', '') if config.DATABRICKS_HOST else '<workspace>'
    print(f"""
To grant the app access to Lakebase as superuser:

1. Go to: {host_display}
2. Navigate to: Compute > Lakebase Postgres > {config.LAKEBASE_INSTANCE_NAME}
3. Click: Permissions tab
4. Click: Add role
5. Enter Service Principal ID: {sp_id}
6. Set Role membership: databricks_superuser
7. Click: Confirm
""")

    return 0 if success else 1


def action_grant_permissions(config, catalog_name: str) -> int:
    """Grant catalog permissions to app service principal."""
    print("Granting Catalog Permissions\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    sp_id, sp_name = get_app_service_principal(config.DATABRICKS_HOST, token, config.APP_NAME)
    if not sp_id:
        print(f"  Could not get service principal for app: {config.APP_NAME}")
        return 1

    print(f"App: {config.APP_NAME}")
    print(f"Service Principal: {sp_id}")
    print(f"Catalog: {catalog_name}")
    print()

    print(f"Granting ALL_PRIVILEGES on catalog '{catalog_name}'...")
    if grant_catalog_permissions(config.DATABRICKS_HOST, token, catalog_name, sp_id):
        print(f"\nSuccessfully granted ALL_PRIVILEGES to {sp_id}")
        return 0
    print(f"\nFailed to grant permissions")
    return 1


def action_deploy(config, source_path: str) -> int:
    """Deploy app source code."""
    print("Deploying App Source Code\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    print(f"App: {config.APP_NAME}")
    print(f"Source Path: {source_path}")
    print()

    if deploy_app_source(config.DATABRICKS_HOST, token, config.APP_NAME, source_path):
        print(f"\nApp deployment initiated")
        return 0
    print(f"\nApp deployment failed")
    return 1


def action_full_info(config) -> int:
    """Get full app information."""
    print("Full App Information\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    app_info = get_full_app_info(config.DATABRICKS_HOST, token, config.APP_NAME)

    if app_info:
        print(f"App Name:               {app_info.get('name')}")
        print(f"App ID:                 {app_info.get('id')}")
        print(f"App URL:                {app_info.get('url')}")
        print(f"Service Principal ID:   {app_info.get('service_principal_client_id')}")
        print(f"Service Principal Name: {app_info.get('service_principal_name')}")
        print(f"App Status:             {app_info.get('app_status', {}).get('state')}")
        print(f"Compute Status:         {app_info.get('compute_status', {}).get('state')}")
        print(f"Creator:                {app_info.get('creator')}")
        print(f"Created:                {app_info.get('create_time')}")

        active_deployment = app_info.get('active_deployment', {})
        if active_deployment:
            print(f"\nActive Deployment:")
            print(f"  Deployment ID:        {active_deployment.get('deployment_id')}")
            print(f"  Status:               {active_deployment.get('status', {}).get('state')}")
            print(f"  Source Path:          {active_deployment.get('source_code_path')}")
        return 0
    print(f"  Could not get app info for: {config.APP_NAME}")
    return 1


def action_add_lakebase_role(config) -> int:
    """Add app service principal as Lakebase database role."""
    print("Adding Lakebase Database Role\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    sp_id, sp_name = get_app_service_principal(config.DATABRICKS_HOST, token, config.APP_NAME)
    if not sp_id:
        print(f"  Could not get service principal for app: {config.APP_NAME}")
        return 1

    print(f"App: {config.APP_NAME}")
    print(f"Service Principal: {sp_id}")
    print(f"Lakebase Instance: {config.LAKEBASE_INSTANCE_NAME}")
    print()

    existing_roles = get_lakebase_roles(config.DATABRICKS_HOST, token, config.LAKEBASE_INSTANCE_NAME)
    for role in existing_roles:
        if role.get('name') == sp_id:
            print(f"  Role already exists: {role.get('membership_role')}")
            return 0

    print(f"Adding DATABRICKS_SUPERUSER role...")
    if add_lakebase_role(config.DATABRICKS_HOST, token, config.LAKEBASE_INSTANCE_NAME, sp_id):
        print(f"\nSuccessfully added Lakebase role for {sp_id}")
        return 0
    print(f"\nFailed to add Lakebase role")
    return 1


def action_list_lakebase_roles(config) -> int:
    """List all Lakebase database roles."""
    print("Lakebase Database Roles\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    print(f"Instance: {config.LAKEBASE_INSTANCE_NAME}\n")

    roles = get_lakebase_roles(config.DATABRICKS_HOST, token, config.LAKEBASE_INSTANCE_NAME)

    if not roles:
        print("No roles found")
        return 0

    for role in roles:
        print(f"  {role.get('identity_type')}: {role.get('name')}")
        print(f"    Role: {role.get('membership_role')}")
        print()

    return 0


def action_link_app_resource(config) -> int:
    """Link Lakebase instance to app as an App Resource for automatic PGPASSWORD injection."""
    print("Linking Lakebase Instance to App Resource\n")

    token = get_databricks_token(config.DATABRICKS_HOST)
    if not token:
        return 1

    print(f"App: {config.APP_NAME}")
    print(f"Lakebase Instance: {config.LAKEBASE_INSTANCE_NAME}")
    print()

    existing_resources = get_app_resources(config.DATABRICKS_HOST, token, config.APP_NAME)
    for resource in existing_resources:
        db = resource.get('database', {})
        if db.get('instance_name') == config.LAKEBASE_INSTANCE_NAME:
            print(f"  Lakebase instance already linked to app")
            print(f"   Instance: {db.get('instance_name')}")
            print(f"   Permission: {db.get('permission')}")
            return 0

    print(f"Linking Lakebase instance with CAN_CONNECT_AND_CREATE permission...")
    if link_app_resource(config.DATABRICKS_HOST, token, config.APP_NAME, config.LAKEBASE_INSTANCE_NAME):
        print(f"\nSuccessfully linked Lakebase instance to app")
        print(f"   Visible in: Databricks UI > Apps > {config.APP_NAME} > Settings > App Resources")
        return 0
    print(f"\nFailed to link Lakebase instance to app")
    return 1


def action_instructions(config) -> int:
    """Print setup instructions."""
    token = get_databricks_token(config.DATABRICKS_HOST)
    sp_id = None

    if token:
        sp_id, _ = get_app_service_principal(config.DATABRICKS_HOST, token, config.APP_NAME)

    print("=" * 60)
    print("LAKEBASE SETUP INSTRUCTIONS")
    print("=" * 60)
    print(f"""
OPTION A: Using Databricks Asset Bundles (Recommended)
======================================================
Lakebase infrastructure can be managed via databricks.yml.

STEP 1: Deploy Infrastructure with DAB
--------------------------------------
   databricks bundle validate
   databricks bundle deploy -t development

STEP 2: Get App Service Principal
---------------------------------
   python scripts/lakebase_manager.py --action app-info

STEP 3: Add App Permission to Lakebase
--------------------------------------
1. Navigate to: Compute > Lakebase Postgres > {config.LAKEBASE_INSTANCE_NAME or '<instance>'}
2. Click: Permissions tab > Add role
3. Enter Service Principal ID: {sp_id or '<from Step 2>'}
4. Set Role membership: databricks_superuser

STEP 4: Update app.yaml with Connection Details
-----------------------------------------------
   LAKEBASE_HOST: <endpoint from connection details>
   LAKEBASE_DATABASE: databricks_postgres
   ENDPOINT_NAME: projects/<project>/branches/<branch>/endpoints/primary  (autoscaling)

STEP 5: Create Tables and Seed Data
-----------------------------------
   ./scripts/setup-lakebase.sh --recreate

STEP 6: Redeploy App
--------------------
   databricks bundle deploy -t development
""")

    return 0


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Lakebase Instance Manager for Databricks Apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lakebase_manager.py --action check
  python lakebase_manager.py --action app-info
  python lakebase_manager.py --action full-info
  python lakebase_manager.py --action status
  python lakebase_manager.py --action grant-permissions --catalog my_catalog
  python lakebase_manager.py --action add-lakebase-role
  python lakebase_manager.py --action list-lakebase-roles
  python lakebase_manager.py --action link-app-resource
  python lakebase_manager.py --action deploy --source-path /Workspace/...
  python lakebase_manager.py --action instructions
        """
    )

    parser.add_argument("--action",
        choices=["check", "app-info", "full-info", "status", "instructions",
                 "grant-permissions", "deploy", "add-lakebase-role", "list-lakebase-roles",
                 "link-app-resource"],
        required=True, help="Action to perform")
    parser.add_argument("--app-name", default=Config.APP_NAME, help="Databricks App name")
    parser.add_argument("--instance-name", default=Config.LAKEBASE_INSTANCE_NAME, help="Lakebase instance name")
    parser.add_argument("--host", default=Config.DATABRICKS_HOST, help="Databricks host URL")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--catalog", default=None, help="Catalog name (for grant-permissions)")
    parser.add_argument("--source-path", default=None, help="Source code path (for deploy)")

    args = parser.parse_args()

    Config.DATABRICKS_HOST = args.host or Config.DATABRICKS_HOST
    Config.LAKEBASE_INSTANCE_NAME = args.instance_name or Config.LAKEBASE_INSTANCE_NAME
    Config.APP_NAME = args.app_name or Config.APP_NAME

    Config.load_from_app_yaml(args.project_root)

    # Resolve DATABRICKS_HOST from CLI profile if still empty
    if not Config.DATABRICKS_HOST:
        try:
            result = subprocess.run(
                ['databricks', 'auth', 'env'],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if line.startswith("DATABRICKS_HOST="):
                    Config.DATABRICKS_HOST = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass

    if not Config.DATABRICKS_HOST:
        print("DATABRICKS_HOST is not configured.")
        print("Set via --host flag, DATABRICKS_HOST env var, or databricks CLI profile.")
        return 1

    actions = {
        "check": lambda: action_check(Config),
        "app-info": lambda: action_app_info(Config),
        "full-info": lambda: action_full_info(Config),
        "status": lambda: action_status(Config),
        "instructions": lambda: action_instructions(Config),
        "grant-permissions": lambda: action_grant_permissions(Config, args.catalog) if args.catalog
            else (print("--catalog is required for grant-permissions action") or 1),
        "deploy": lambda: action_deploy(Config, args.source_path) if args.source_path
            else (print("--source-path is required for deploy action") or 1),
        "add-lakebase-role": lambda: action_add_lakebase_role(Config),
        "list-lakebase-roles": lambda: action_list_lakebase_roles(Config),
        "link-app-resource": lambda: action_link_app_resource(Config),
    }

    handler = actions.get(args.action)
    return handler() if handler else 1


if __name__ == "__main__":
    sys.exit(main())

# Lakebase Database Setup

Helper scripts for managing Lakebase PostgreSQL tables and permissions in Databricks Apps.

## Directory Structure

```
db/lakebase/
├── README.md         # This file
├── ddl/              # Your table DDL .sql files
└── dml_seed/         # Your seed data .sql files
```

## Quick Start

### 1. Add Your DDL Files

Create SQL files in `db/lakebase/ddl/`:

```sql
-- db/lakebase/ddl/01_your_table.sql
CREATE TABLE IF NOT EXISTS ${schema}.your_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Add Seed Data (Optional)

Create SQL files in `db/lakebase/dml_seed/`:

```sql
-- db/lakebase/dml_seed/01_seed_your_table.sql
INSERT INTO ${schema}.your_table (name) VALUES ('Example');
```

### 3. Setup Permissions

Before your app can access Lakebase, setup permissions:

```bash
# Setup all permissions at once
python scripts/lakebase_manager.py --action setup-all-permissions --catalog your_catalog

# Or via deploy script
./scripts/deploy.sh --setup-permissions --catalog your_catalog
```

### 4. Run Table Setup

```bash
./scripts/setup-lakebase.sh --recreate
```

## Permission Types

Your app needs three types of permissions to access Lakebase:

| Permission | API | Purpose |
|------------|-----|---------|
| **Unity Catalog** | `PATCH /api/2.1/unity-catalog/permissions/catalog/{catalog}` | ALL_PRIVILEGES on catalog for schema/table access |
| **Database Role** | `POST /api/2.0/database/instances/{instance}/roles` | DATABRICKS_SUPERUSER for PostgreSQL operations |
| **App Resource** | `PATCH /api/2.0/apps/{app}` | CAN_CONNECT_AND_CREATE for automatic PGPASSWORD injection |

## Commands

### Table Management

```bash
# Setup tables + seed data
./scripts/setup-lakebase.sh

# Recreate tables (drops existing)
./scripts/setup-lakebase.sh --recreate

# Check table status
./scripts/setup-lakebase.sh --status

# Drop tables
./scripts/setup-lakebase.sh --drop
```

### Permission Management

```bash
# Setup ALL permissions at once (recommended)
python scripts/lakebase_manager.py --action setup-all-permissions --catalog my_catalog

# Individual permission commands:
# 1. Grant Unity Catalog permissions
python scripts/lakebase_manager.py --action grant-permissions --catalog my_catalog

# 2. Add Lakebase database role
python scripts/lakebase_manager.py --action add-lakebase-role

# 3. Link Lakebase as app resource
python scripts/lakebase_manager.py --action add-app-resource

# List existing roles
python scripts/lakebase_manager.py --action list-lakebase-roles
```

### Status & Info

```bash
# Full status check
python scripts/lakebase_manager.py --action status

# Check connectivity
python scripts/lakebase_manager.py --action check

# Get app service principal info
python scripts/lakebase_manager.py --action app-info

# Get Lakebase instance connection details
python scripts/lakebase_manager.py --action instance-info

# Get setup instructions
python scripts/lakebase_manager.py --action instructions
```

### Full Deployment

```bash
# Full deployment: create app + permissions + tables
./scripts/deploy.sh --full --catalog my_catalog

# Deploy app + setup permissions
./scripts/deploy.sh --setup-permissions --catalog my_catalog

# Deploy app + setup tables
./scripts/deploy.sh --with-lakebase

# Only setup tables (skip app deployment)
./scripts/deploy.sh --lakebase-only
```

## SQL Format

Use `${schema}` placeholder - replaced at runtime with `LAKEBASE_SCHEMA` from app.yaml.

Example:

```sql
CREATE TABLE IF NOT EXISTS ${schema}.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);
```

## Configuration

Update these environment variables in `app.yaml`:

```yaml
env:
  - name: LAKEBASE_HOST
    value: "your-instance.database.cloud.databricks.com"
  - name: LAKEBASE_DATABASE
    value: "databricks_postgres"
  - name: LAKEBASE_SCHEMA
    value: "your_schema_name"
  - name: LAKEBASE_PORT
    value: "443"
  - name: LAKEBASE_USER
    value: "databricks"
```

Get connection details from Databricks UI:
`Compute > Lakebase Postgres > <instance-name> > Connection details`

## Environment Variables

The scripts read from these environment variables (with app.yaml fallback):

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Databricks workspace URL |
| `APP_NAME` | Databricks App name |
| `LAKEBASE_INSTANCE_NAME` | Lakebase instance name |
| `LAKEBASE_HOST` | Lakebase PostgreSQL endpoint |
| `LAKEBASE_DATABASE` | Database name (usually `databricks_postgres`) |
| `LAKEBASE_SCHEMA` | Schema for your tables |
| `LAKEBASE_PORT` | PostgreSQL port (usually `443`) |
| `LAKEBASE_USER` | Database user (usually `databricks`) |

## Troubleshooting

### Permission Errors

If you get permission errors when accessing Lakebase:

```bash
# Check current permissions
python scripts/lakebase_manager.py --action status

# Setup all permissions
python scripts/lakebase_manager.py --action setup-all-permissions --catalog your_catalog
```

### Connection Errors

```bash
# Verify Lakebase instance is running
python scripts/lakebase_manager.py --action instance-info

# Check connectivity
python scripts/lakebase_manager.py --action check
```

### Missing PGPASSWORD

If your app can't authenticate to Lakebase:

```bash
# Link Lakebase as app resource (enables automatic PGPASSWORD)
python scripts/lakebase_manager.py --action add-app-resource
```

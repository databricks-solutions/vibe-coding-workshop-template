# Lakebase Database Setup

Helper scripts for managing Lakebase PostgreSQL tables and permissions in Databricks Apps.
Supports both **Autoscaling** (preferred) and **Provisioned** (legacy) Lakebase tiers.

## Lakebase Tiers

| Aspect | Autoscaling | Provisioned |
|--------|------------|-------------|
| CLI namespace | `databricks postgres` | `databricks database` |
| Resource model | Project > Branch > Endpoint | Flat Instance |
| ENDPOINT_NAME | `projects/<name>/branches/<branch>/endpoints/<ep>` | N/A |
| Port | 5432 | 5432 |
| Scale-to-zero | Yes | No |
| Mode auto-detect | ENDPOINT_NAME starts with `projects/` | Otherwise |

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
# Grant Unity Catalog permissions
python scripts/lakebase_manager.py --action grant-permissions --catalog your_catalog

# Add Lakebase database role
python scripts/lakebase_manager.py --action add-lakebase-role

# Link Lakebase as app resource (enables automatic PGPASSWORD)
python scripts/lakebase_manager.py --action link-app-resource
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
# 1. Grant Unity Catalog permissions
python scripts/lakebase_manager.py --action grant-permissions --catalog my_catalog

# 2. Add Lakebase database role
python scripts/lakebase_manager.py --action add-lakebase-role

# 3. Link Lakebase as app resource
python scripts/lakebase_manager.py --action link-app-resource

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

# Get full app details
python scripts/lakebase_manager.py --action full-info

# Get setup instructions
python scripts/lakebase_manager.py --action instructions
```

### Full Deployment

```bash
# Full deployment: bundle + permissions + tables
./scripts/deploy.sh

# Code-only quick deploy
./scripts/deploy.sh --code-only

# Only setup tables (skip app deployment)
./scripts/deploy.sh --tables-only
```

## SQL Format

Use `${schema}` placeholder -- replaced at runtime with `LAKEBASE_SCHEMA` from app.yaml.

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
    value: "your-endpoint.database.us-east-1.cloud.databricks.com"
  - name: LAKEBASE_DATABASE
    value: "databricks_postgres"
  - name: LAKEBASE_SCHEMA
    value: "your_schema_name"
  - name: LAKEBASE_PORT
    value: "5432"
  - name: ENDPOINT_NAME
    value: "projects/your-project/branches/main/endpoints/primary"
```

Get connection details from Databricks UI:
`Compute > Lakebase Postgres > <instance-name> > Connection details`

## Environment Variables

The scripts read from these environment variables (with app.yaml fallback):

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Databricks workspace URL |
| `APP_NAME` | Databricks App name |
| `LAKEBASE_INSTANCE_NAME` | Lakebase instance / project name |
| `LAKEBASE_HOST` | Lakebase PostgreSQL endpoint |
| `LAKEBASE_DATABASE` | Database name (usually `databricks_postgres`) |
| `LAKEBASE_SCHEMA` | Schema for your tables |
| `LAKEBASE_PORT` | PostgreSQL port (5432) |
| `LAKEBASE_MODE` | `autoscaling` or `provisioned` (auto-detected from ENDPOINT_NAME) |
| `ENDPOINT_NAME` | Autoscaling endpoint path (from app.yaml) |
| `PRODUCTION_SCHEMA` | Schema name requiring extra confirmation on recreate |

## Troubleshooting

### Permission Errors

```bash
python scripts/lakebase_manager.py --action status
```

### Connection Errors

```bash
python scripts/lakebase_manager.py --action check
```

### Missing PGPASSWORD

```bash
# Link Lakebase as app resource (enables automatic PGPASSWORD)
python scripts/lakebase_manager.py --action link-app-resource
```

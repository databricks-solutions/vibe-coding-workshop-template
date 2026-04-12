# Lakebase Plugin

**Upstream docs (always check for latest):** https://databricks.github.io/appkit/docs/plugins/lakebase
Also consult the live AppKit docs: `npx @databricks/appkit docs "lakebase"`
The information below may be outdated. Prefer upstream when available.

PostgreSQL connection pool for Databricks Lakebase Autoscaling with automatic OAuth token refresh.

**Capabilities:** Standard `pg.Pool`, automatic OAuth token refresh (1-hour tokens, 2-minute buffer), token caching, OpenTelemetry instrumentation.

## Adding to an Existing AppKit Project

### 1. Install the Package

```bash
npm install @databricks/lakebase
```

### 2. Register the Plugin

In `server/server.ts`:

```typescript
import { createApp, lakebase, server } from "@databricks/appkit";

await createApp({
  plugins: [server(), lakebase()],
});
```

### 3. Environment Variables

Add to `.env` for local development:

```env
LAKEBASE_ENDPOINT=projects/<project>/branches/<branch>/endpoints/<endpoint>
PGHOST=<your-lakebase-host>
PGDATABASE=<database-name>
PGSSLMODE=require
```

Add to `app.yaml` for deployed apps (Lakebase Autoscaling):

```yaml
env:
  - name: LAKEBASE_ENDPOINT
    value: 'projects/<project-id>/branches/production/endpoints/primary'
  - name: PGHOST
    value: '<endpoint-hostname>'
  - name: PGDATABASE
    value: 'databricks_postgres'
  - name: PGSSLMODE
    value: 'require'
```

**Two valid deployment patterns exist:**

1. **Resource binding (upstream default):** If the app was scaffolded with `databricks apps init --features lakebase` or has `postgres_project`/`postgres_branch`/`postgres_endpoint` resources in `databricks.yml`, the platform auto-injects `PGHOST`, `PGDATABASE`, `PGSSLMODE`, `PGUSER`, `PGPORT`, and `PGAPPNAME`. Only `LAKEBASE_ENDPOINT` needs to be set explicitly:
   ```yaml
   env:
     - name: LAKEBASE_ENDPOINT
       valueFrom: postgres
   ```
   Reference: [AppKit Lakebase docs - Environment variables](https://databricks.github.io/appkit/docs/plugins/lakebase#environment-variables)

2. **Static env vars (manual setup):** If the Lakebase project was created via CLI without a bundle resource declaration, set all PG variables explicitly as static values in `app.yaml` (as shown above). Do NOT set `PGUSER` or `PGPASSWORD` — the plugin handles OAuth token rotation automatically.

### 4. Lakebase Resources in databricks.yml (Optional)

For Lakebase Autoscaling, `databricks.yml` does **not** require a postgres resource for the app to connect (if using static env vars in `app.yaml`). However, if you want `valueFrom: postgres` auto-injection or bundle-managed project lifecycle, declare `postgres_project`/`postgres_branch`/`postgres_endpoint` resources (CLI v0.287.0+).

> **Do NOT use the old `postgres:` resource format** (with `branch:` / `database:` / `permission:` fields). That format is for Lakebase Provisioned only and will be rejected by the bundle deployer for Autoscaling projects.

**Optional: Bundle-managed Lakebase project lifecycle.** If you want the bundle to create and manage the Lakebase Autoscaling project (instead of using CLI commands), use `postgres_project`, `postgres_branch`, and `postgres_endpoint` resources (Databricks CLI v0.287.0+):

```yaml
resources:
  postgres_projects:
    my_db:
      project_id: <project-name>
      display_name: '<display-name>'
      pg_version: 17
      default_endpoint_settings:
        autoscaling_limit_min_cu: 0.5
        autoscaling_limit_max_cu: 2.0
        suspend_timeout_duration: "300s"

  postgres_branches:
    main:
      parent: ${resources.postgres_projects.my_db.id}
      branch_id: production
      is_protected: false
      no_expiry: true

  postgres_endpoints:
    primary:
      parent: ${resources.postgres_branches.main.id}
      endpoint_id: primary
      endpoint_type: ENDPOINT_TYPE_READ_WRITE
      autoscaling_limit_min_cu: 0.5
      autoscaling_limit_max_cu: 2.0
      suspend_timeout_duration: "300s"
```

This manages the project lifecycle through the bundle but does **not** create an app resource binding. You still need static env vars in `app.yaml` and manual SP grants. Reference: [DABs postgres_project docs](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#postgres_project)

### 5. Create a Lakebase Project First

Before using the plugin, you need a Lakebase Postgres Autoscaling project. Create one via:
- The Databricks UI (Compute > Lakebase Postgres)
- Or: `databricks postgres create-project --name <project-name>`

Then retrieve the host from the endpoint listing:
```bash
databricks postgres list-endpoints projects/<project-name>/branches/production --output json
```

### Autoscaling and Scale-to-Zero

New Lakebase endpoints default to `suspend_timeout_duration: "0s"`, which means **always on** (no auto-suspend). To enable scale-to-zero and save cost during development, set a positive duration:

```bash
# "spec" is the UPDATE_MASK positional arg — tells the API which top-level field to patch
databricks postgres update-endpoint \
  projects/<project>/branches/production/endpoints/primary spec \
  --json '{"spec": {"autoscaling_limit_min_cu": 0.5, "autoscaling_limit_max_cu": 2.0, "suspend_timeout_duration": "300s"}}' \
  --profile <PROFILE>
```

- `suspend_timeout_duration: "300s"` -- scales to zero after 5 minutes idle
- `autoscaling_limit_min_cu: 0.5` -- minimum compute when active
- `autoscaling_limit_max_cu: 2.0` -- sufficient for development

The endpoint wakes automatically on the next connection attempt (may take a few seconds on first request).

### 6. Using the Pool

Use a schema name scoped to the user or app (e.g., `prashanth_s_booking_app`) to avoid collisions when multiple apps share a database. Avoid generic names like `app` or `public`. Pass the schema as a `DB_SCHEMA` environment variable.

```typescript
const AppKit = await createApp({
  plugins: [server(), lakebase()],
});

const DB_SCHEMA = process.env.DB_SCHEMA || "app";

await AppKit.lakebase.query(`CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA}`);

await AppKit.lakebase.query(`CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.orders (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)`);

const result = await AppKit.lakebase.query(
  `SELECT * FROM ${DB_SCHEMA}.orders WHERE user_id = $1`,
  [userId],
);

// Raw pg.Pool for ORMs or advanced usage
const pool = AppKit.lakebase.pool;

// ORM-ready config objects
const ormConfig = AppKit.lakebase.getOrmConfig();
const pgConfig = AppKit.lakebase.getPgConfig();
```

## Data Architecture: Analytics vs CRUD

When an app uses both `analytics()` and `lakebase()` plugins, decide which data goes where:

- **Analytics / Reporting (read-only aggregations):** SQL Warehouse via `useAnalyticsQuery("queryKey", params)` — revenue trends, user counts, status breakdowns
- **Transactional / CRUD (data users create/update/delete):** Lakebase via `fetch('/api/...')` or custom `useLakebaseData()` hook — bookings, reviews, user profiles, orders

**Rule of thumb:** If the UI has a "Create", "Edit", or "Delete" button for the data, it belongs in Lakebase. If it is a read-only chart or dashboard metric, it stays on the SQL warehouse.

AppKit chart components (`BarChart`, `AreaChart`, `DonutChart`, `DataTable`) that use the `queryKey` prop are bound to the analytics plugin. Only convert pages that fetch data manually (via `fetch()`) to Lakebase API calls.

## Pool Configuration

```typescript
await createApp({
  plugins: [
    lakebase({
      pool: {
        max: 10,                       // default: 10
        connectionTimeoutMillis: 5000, // default: 10000
        idleTimeoutMillis: 30000,      // default: 30000
      },
    }),
  ],
});
```

## Database Permissions

**With resource binding (scaffolded via `databricks apps init`):** The Service Principal is automatically granted `CONNECT_AND_CREATE` permission on the `postgres` resource. This lets the SP connect and create new objects, but not access existing schemas or tables. No manual SQL grants are needed for initial setup.

**Without resource binding (manual CLI setup):** The SP does not automatically receive permissions. It gets ownership of any objects it creates (schemas, tables, sequences) through DDL in `server.ts`. If the SP encounters permission errors on first deploy, grant via the Lakebase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS databricks_auth;
SELECT databricks_create_role('<SP_CLIENT_ID>', 'service_principal');
GRANT CONNECT ON DATABASE databricks_postgres TO "<SP_CLIENT_ID>";
GRANT CREATE, USAGE ON SCHEMA public TO "<SP_CLIENT_ID>";
```

Reference: [AppKit Lakebase docs - Database Permissions](https://databricks.github.io/appkit/docs/plugins/lakebase#database-permissions)

### Local Development

1. **Deploy the app first** — the Service Principal creates schemas/tables on first deploy. Deploying first matters because `databricks_superuser` grants DML access (read/write) but NOT DDL (create schema/table).
2. **Grant `databricks_superuser` via the Lakebase UI (recommended):**
   - Open the Lakebase Autoscaling UI > your project's Branch Overview page
   - Click **Add role** (or **Edit role** if your OAuth role already exists)
   - Select your Databricks identity and check the **`databricks_superuser`** system role
   - Reference: [AppKit Lakebase docs - Local development](https://databricks.github.io/appkit/docs/plugins/lakebase#local-development)
3. **Run locally** — your Databricks email is used for OAuth authentication.

**Alternative: Fine-grained SQL grants.** If you need schema-level control instead of superuser, use the SQL grant script in the [upstream docs](https://databricks.github.io/appkit/docs/plugins/lakebase#fine-grained-permissions). Deploy first so the SP initializes objects.

## Gotchas

For the complete list of Lakebase runtime gotchas (DECIMAL coercion, DATE handling,
seed idempotency, Express import restrictions, and more), **you MUST read the Gotchas
table in `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md`** when building
CRUD routes or wiring the frontend.

The one gotcha specific to plugin setup (not wiring):
- **Endpoint hostnames change when endpoints are recreated.** Always fetch the current
  host dynamically via `databricks postgres get-endpoint ... | jq -r '.status.hosts.host'`
  rather than relying on `.env` values from a previous session.

## Generating Credentials for CLI/Script Access

Lakebase uses OAuth token authentication — not traditional PostgreSQL username/password credentials. When connecting via `psql`, `node-pg` scripts, or any ad-hoc tool outside the AppKit plugin:

- The **username** is the caller's Databricks email (for users) or SP client ID (for service principals)
- The **password** is a short-lived JWT token from `generate-database-credential` (expires in ~1 hour)
- The AppKit lakebase plugin handles this transparently; manual credentials are only needed for ad-hoc scripts

```bash
# The endpoint path is a REQUIRED positional argument
ENDPOINT="projects/<project>/branches/production/endpoints/primary"
CREDS=$(databricks postgres generate-database-credential "$ENDPOINT" \
  --profile $PROFILE --output json)

# Username is your Databricks email, NOT from the creds response
export PGUSER="$(databricks current-user me --output json --profile $PROFILE | jq -r '.userName')"
# Password is the .token field, NOT .username/.password (those fields don't exist)
export PGPASSWORD=$(echo "$CREDS" | jq -r '.token')
```

**Tip:** [Postgres password authentication](https://docs.databricks.com/aws/en/oltp/projects/authentication#overview) is a simpler alternative that avoids OAuth complexity for ad-hoc access. Set up a password in the Branch Overview page of the Lakebase UI.

## Combining with Other Plugins

```typescript
import { createApp, server, lakebase, analytics } from "@databricks/appkit";

await createApp({
  plugins: [server(), lakebase(), analytics()],
});
```

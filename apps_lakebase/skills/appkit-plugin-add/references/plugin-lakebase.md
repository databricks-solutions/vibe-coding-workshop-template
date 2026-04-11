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

Add to `app.yaml` for deployed apps:

```yaml
env:
  - name: LAKEBASE_ENDPOINT
    valueFrom: postgres
```

When deployed with a `postgres` database resource, `PGHOST`, `PGDATABASE`, `PGSSLMODE`, `PGUSER`, `PGPORT`, and `PGAPPNAME` are auto-injected by the platform. Only `LAKEBASE_ENDPOINT` must be set explicitly.

### 4. Create a Lakebase Project First

Before using the plugin, you need a Lakebase Postgres Autoscaling project. Create one via:
- The Databricks UI (Compute > Lakebase Postgres)
- Or: `databricks postgres projects create --name <project-name>`

Then create a branch and database within the project.

### 5. Using the Pool

```typescript
const AppKit = await createApp({
  plugins: [server(), lakebase()],
});

// Direct query
await AppKit.lakebase.query(`CREATE SCHEMA IF NOT EXISTS app`);

await AppKit.lakebase.query(`CREATE TABLE IF NOT EXISTS app.orders (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)`);

const result = await AppKit.lakebase.query(
  "SELECT * FROM app.orders WHERE user_id = $1",
  [userId],
);

// Raw pg.Pool for ORMs or advanced usage
const pool = AppKit.lakebase.pool;

// ORM-ready config objects
const ormConfig = AppKit.lakebase.getOrmConfig();
const pgConfig = AppKit.lakebase.getPgConfig();
```

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

When you create the app with the Lakebase resource, the Service Principal gets `CONNECT_AND_CREATE` permission automatically.

### Local Development

1. **Deploy the app first** — the Service Principal creates schemas/tables on first deploy.
2. **Grant `databricks_superuser`** via the Lakebase UI (Branch Overview > Add role).
3. **Run locally** — your Databricks identity is used for OAuth authentication.

The `databricks_superuser` role gives full DML access (read/write) but not DDL (create schema/table). Deploy first so the Service Principal creates all objects.

## Combining with Other Plugins

```typescript
import { createApp, server, lakebase, analytics } from "@databricks/appkit";

await createApp({
  plugins: [server(), lakebase(), analytics()],
});
```

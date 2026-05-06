# AppKit App Management Reference

> **Upstream docs (always check for latest):**
> - https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-apps/references
> - https://databricks.github.io/appkit/docs/app-management
> - https://databricks.github.io/appkit/docs/configuration
> - `databricks apps deploy --help`

## app.yaml Configuration

The `app.yaml` file configures the app's runtime environment in Databricks Apps.

```yaml
# AppKit canonical command (runs the tsdown-built server output)
command:
  - node
  - build/index.mjs

# Alternative: delegates to package.json "start" script
# command:
#   - npm
#   - run
#   - start

env:
  - name: DATABRICKS_WAREHOUSE_ID
    valueFrom: sql-warehouse
```

### Common Environment Bindings

| Env Var | `valueFrom` | Plugin |
|---------|-------------|--------|
| `DATABRICKS_WAREHOUSE_ID` | `sql-warehouse` | Analytics, Genie |
| `LAKEBASE_ENDPOINT` | `postgres` | Lakebase |
| `DATABRICKS_VOLUME_*` | `volume` | Files |

> **Lakebase env vars:** Use `valueFrom: postgres` in `app.yaml` with bundle-managed `postgres_project`/`postgres_branch`/`postgres_endpoint` resources in `databricks.yml`. The platform auto-injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE`.

## Deploy Command

```bash
databricks apps deploy [--profile PROFILE]
```

Runs the full pipeline: build frontend, deploy bundle, start app.

### Options

| Flag | Effect |
|------|--------|
| `--skip-build` | Skip `npm run build` for faster iteration |
| `--force` | Override Git branch validation |
| `--target TARGET` | Deploy to a specific target (e.g., `prod`) |
| `--var "key=value"` | Pass custom variables |

## Validate Configuration

```bash
databricks apps validate [--profile PROFILE]
```

Checks `app.yaml` schema, resource bindings, and manifest validity before deploying.

## App Lifecycle Commands

```bash
databricks apps start <name> --profile <PROFILE>    # Start a stopped app
databricks apps stop <name> --profile <PROFILE>     # Stop without deleting
databricks apps get <name> --profile <PROFILE>      # Detailed app info (URL, status, SP ID)
databricks apps list --profile <PROFILE>            # List all apps
databricks apps delete <name> --profile <PROFILE>   # Permanently delete (irreversible)
```

`--profile` is required for all `databricks` CLI commands in multi-workspace setups. It is not needed for `npm` commands.

## Log Streaming

```bash
databricks apps logs <name> --profile <PROFILE>   # Last 200 lines, then exit
```

### Options

| Flag | Effect |
|------|--------|
| `--tail-lines N` | Show last N lines |
| `--follow` | Stream logs in real-time |
| `--search PATTERN` | Filter by pattern |
| `--source APP\|SYSTEM` | Filter by log source |
| `--output-file PATH` | Save to file |
| `--timeout DURATION` | Stop after duration (e.g., `5m`) |

### Examples

```bash
databricks apps logs my-app --tail-lines 50 --profile <PROFILE>
databricks apps logs my-app --follow --search ERROR --profile <PROFILE>
databricks apps logs my-app --follow --source APP --profile <PROFILE>
databricks apps logs my-app --follow --output-file app.log --profile <PROFILE>
databricks apps logs my-app --follow --timeout 5m --profile <PROFILE>
```

## Environment Variables

### Auto-injected by Databricks Apps Runtime

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL (e.g., `https://xxx.cloud.databricks.com`) |
| `DATABRICKS_APP_PORT` | Port to bind (default: 8000) |
| `DATABRICKS_APP_NAME` | App name in Databricks |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABRICKS_WORKSPACE_ID` | Workspace ID | Auto-fetched from API |
| `NODE_ENV` | `"development"` or `"production"` | — |

### Telemetry

| Variable | Description |
|----------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint |
| `OTEL_SERVICE_NAME` | Service name for traces |

## Local Development Authentication

**Option 1 — Databricks CLI (recommended):**

```bash
databricks auth login --host <HOST> --profile <PROFILE>
npm run dev                                    # uses DEFAULT profile
DATABRICKS_CONFIG_PROFILE=my-profile npm run dev  # specific profile
```

**Option 2 — Environment variables:**

```bash
export DATABRICKS_HOST="https://xxx.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."
export DATABRICKS_WAREHOUSE_ID="abc123..."
npm run dev
```

**Option 3 — `.env` file** (auto-loaded by AppKit, add to `.gitignore`):

```env
DATABRICKS_HOST=https://xxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_WAREHOUSE_ID=abc123...
```

## Platform Constraints

Source: [databricks-agent-skills platform-guide.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/platform-guide.md)

| Constraint | Value |
|------------|-------|
| Startup timeout | 10 minutes (including dependency installation) |
| HTTP proxy timeout | 120 seconds per request (not configurable) |
| Max apps per workspace | 100 |
| Max file size | 10 MB per file |
| Filesystem | Ephemeral (no persistent local storage) |
| Graceful shutdown | SIGTERM → 15s → SIGKILL |
| Logging | stdout/stderr only; file-based logs lost on recycle |

| Compute Size | RAM | vCPU | DBU/hour |
|-------------|-----|------|----------|
| Medium (default) | 6 GB | Up to 2 | 0.5 |
| Large | 12 GB | Up to 4 | 1.0 |

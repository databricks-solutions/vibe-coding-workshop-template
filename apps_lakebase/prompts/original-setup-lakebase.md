## Context

You are a full-stack developer adding the Lakebase (PostgreSQL) package to an existing AppKit application and configuring bundle resources for deployment. This is a **config-only** step — install the npm package and configure YAML files, but do NOT modify `server.ts`. Plugin registration happens in the **Wire Lakebase Backend** step.

Key requirements:

- Install `@databricks/lakebase` npm package (do NOT register the plugin in `server.ts` yet)
- Declare `postgres_projects` resource in `databricks.yml` (do NOT declare `postgres_branches` or `postgres_endpoints` — Lakebase auto-creates these)
- Configure `app.yaml` with `valueFrom: postgres` for `LAKEBASE_ENDPOINT` and a static `DB_SCHEMA`
- Derive `DB_SCHEMA` from `$APP_NAME` (hyphens to underscores) for user-scoped database isolation
- Do NOT deploy in this step — deployment happens in the **Deploy and E2E Test** step
- Do NOT create a Lakebase project via CLI — the bundle creates it automatically on first deploy
- Do NOT add `lakebase()` to `server.ts` — that happens in the **Wire Lakebase Backend** step

This prompt is returned as-is for direct use in Cursor/Copilot. No LLM processing.

---

## Your Task

Install the Lakebase (PostgreSQL) package and configure bundle resources so the platform auto-provisions Lakebase on deploy. This is a **config-only** step — install the npm package and configure YAML files. Do NOT modify `server.ts` — plugin registration and database code happen in the **Wire Lakebase Backend** step.

**First:** Read `apps_lakebase/$APP_NAME/.vibecoding-state.md` if it exists — it contains resolved issues and variable values from prior phases.

**Workspace:** `https://adb-4101016551133680.0.azuredatabricks.net/`

**Working directory:** All app code and commands use the `apps_lakebase/` folder. The scaffolded AppKit app lives at `apps_lakebase/$APP_NAME/`.

> **Important:** The CLI profile used here must point to the target workspace. If this differs from the profile used in the **Scaffold, Build & Test** step, update `$PROFILE` accordingly.

---

### Step 1: Set Variables

```bash
USER_JSON=$(databricks current-user me --output json)
EMAIL=$(echo "$USER_JSON" | jq -r '.userName')
FIRSTNAME=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f1)
LASTINITIAL=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f2 | cut -c1)
APP_PREFIX="${FIRSTNAME}-${LASTINITIAL}"
APP_NAME="${APP_PREFIX}-booking-app"
DB_SCHEMA=$(echo "$APP_NAME" | tr '-' '_')
echo "APP_NAME=$APP_NAME  DB_SCHEMA=$DB_SCHEMA"
```

---

### Step 2: Install the Lakebase Package

```bash
cd apps_lakebase/$APP_NAME
npm install @databricks/lakebase
```

---

### Step 3: Add Bundle Resources to `databricks.yml`

Lakebase Autoscaling uses a **two-phase** deploy process because the database ID is auto-generated and cannot be known until the project exists:

- **Phase 1 (this step):** Declare `postgres_projects` only. The first deploy creates the project. Lakebase automatically creates a default `production` branch and `primary` endpoint.
- **Phase 2 (Deploy and E2E Test step):** After the project exists, discover the database ID and add the `app.resources.postgres` binding so `valueFrom: postgres` resolves.

> **The first deploy WILL show the app in CRASHED state.** This is expected — `valueFrom: postgres` cannot resolve until `app.resources.postgres` is configured in Phase 2. Proceed to database ID discovery; the second deploy will succeed.

> **Do NOT declare `postgres_branches` or `postgres_endpoints`** in `databricks.yml`. Lakebase Autoscaling auto-creates these with the project. Declaring them causes Terraform errors: `branch already exists` / `read_write endpoint already exists`.

Add the following to `databricks.yml`:

```yaml
resources:
  postgres_projects:
    my_db:
      project_id: <APP_NAME>
      display_name: '<APP_NAME>'
      pg_version: 17
      default_endpoint_settings:
        autoscaling_limit_min_cu: 0.5
        autoscaling_limit_max_cu: 2.0
        suspend_timeout_duration: "300s"
```

Replace `<APP_NAME>` with the actual `$APP_NAME` value. If `databricks.yml` already has a `resources:` section, merge the `postgres_projects` resource into it.

> **Pre-existing project?** If the Lakebase project already exists (from a prior deploy or manual creation), remove the `postgres_projects` declaration entirely and skip to Phase 2. Bundle deploy will fail with "project already exists" if you try to re-create it.

For the full two-phase reference including the `app.resources.postgres` schema and database ID discovery, see `@apps_lakebase/skills/04-appkit-plugin-add/references/plugin-lakebase.md` section "3. Declare Bundle Resources".

---

### Step 4: Configure `app.yaml` Environment Variables

Add to the `env:` section of `app.yaml`:

```yaml
  - name: LAKEBASE_ENDPOINT
    valueFrom: postgres
  - name: DB_SCHEMA
    value: '<value of $DB_SCHEMA from Step 1>'
```

The platform auto-injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE`, `PGUSER` from the bundle resource binding. Do NOT set these manually.

---

### Step 5: Configure `.env` for Local Development

Add to `.env` in the app root:

```env
DB_SCHEMA=<value of $DB_SCHEMA from Step 1>
```

Local development uses mock fallback data before the first deploy.

---

### Step 6: Verify Package Installation

```bash
cd apps_lakebase/$APP_NAME
npm ls @databricks/lakebase
```

Must show `@databricks/lakebase` in the dependency tree.

---

### Checklist

- [ ] `@databricks/lakebase` installed in `package.json`
- [ ] `server/server.ts` is **unchanged** (plugin registration happens in the Wire Lakebase Backend step)
- [ ] `DB_SCHEMA` derived from `$APP_NAME` (hyphens to underscores)
- [ ] `databricks.yml` has `postgres_projects` resource (no `postgres_branches` or `postgres_endpoints` — auto-created)
- [ ] `app.yaml` has `LAKEBASE_ENDPOINT` with `valueFrom: postgres` and `DB_SCHEMA` as static value
- [ ] `.vibecoding-state.md` updated (see below)

**Before finishing**, append to `apps_lakebase/$APP_NAME/.vibecoding-state.md` with:
- Step name (`## Setup Lakebase`)
- Key variable values (`DB_SCHEMA`, bundle resource project_id)
- Any resolved issues or workarounds encountered during this phase

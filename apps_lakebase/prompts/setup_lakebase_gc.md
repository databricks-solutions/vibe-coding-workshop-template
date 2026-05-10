## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

You are Genie Code, an AI assistant on the Databricks workspace. You are adding the Lakebase (PostgreSQL) package to an existing AppKit application and creating a Lakebase database instance. This is a **config-only** step — create the database instance, bind it to the app, add the npm dependency, and configure YAML files, but do NOT modify `server.ts`. Plugin registration happens in the **Wire Lakebase Backend** step.

Key requirements:

- Create a Lakebase database instance via the **Databricks SDK** (`w.database` / `w.postgres` APIs)
- Apply Lakebase **boilerplate** from `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` Steps 2b–2c via `write_file()` (MCP not used — snippets come from the skill + `GENIE-CODE-OVERRIDES.md`)
- Grant the app's service principal `DATABRICKS_SUPERUSER` access
- Bind the database as a `postgres`-type resource on the app via `w.apps.update()` (AppKit requires `AppResourcePostgres`, not `AppResourceDatabase`)
- Discover the database path via **`w.postgres.list_databases(parent=branch_path)`** (Postgres API — not `w.database.list_databases`) for the resource binding
- Add `@databricks/lakebase` to `package.json` dependencies (do NOT register the plugin in `app.ts` yet)
- Configure `app.yaml` with `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA` environment variables
- Do NOT deploy in this step — deployment happens in `deploy_and_test_gc.md`
- Do NOT add `lakebase()` to `app.ts` — that happens in `wire_ui_to_lakebase_gc.md`

**Environment:** Genie Code on Databricks workspace (serverless). No CLI, no npm, no Node.js. Databricks SDK handles Lakebase provisioning, permissions, resource binding, and all file writes (`write_file`).

**Prompt sequence:** `one-ui-design-local.md` → **this file** → `wire_ui_to_lakebase_gc.md` → `deploy_and_test_gc.md` (see `@apps_lakebase/prompts/README.md`).

---

### Session Recovery: SDK bootstrap

> **Skip** if `w`, `APP_BASE`, and `write_file` are still in scope. If the session was reset, re-run **`@apps_lakebase/gc-prompt-conversion/workshop-variables.md`** three-cell bootstrap (**Cell 1** `%pip install databricks-sdk`, **Cell 2** `restartPython`, **Cell 3** full paste).

> **Troubleshooting:** See `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` for error resolution.

### Required: Verify Databricks SDK Version

The Lakebase resource binding (Step 2) requires `AppResourcePostgres` from a recent SDK. This was installed in the first workshop prompt. Verify it is available:

```python
from databricks.sdk.service.apps import AppResourcePostgres
print("✓ SDK version OK — AppResourcePostgres available")
```

If this fails with `ImportError`, run:

```python
%pip install --upgrade databricks-sdk -q
dbutils.library.restartPython()
```

---

## Your Task

Create a Lakebase database instance, configure the app to connect to it, and add the npm dependency. Do NOT modify `server.ts` — plugin registration and DDL/seed happen in `wire_ui_to_lakebase_gc.md`.

**First:** Read `apps_lakebase/{APP_NAME}/.vibecoding-state.md` if it exists — it contains resolved issues and variable values from prior phases.

**Working directory:** All app files are under `apps_lakebase/{APP_NAME}/` within the repo.

---

### Step 1: Set Variables

Use `spark.sql("SELECT current_user()")` to get the current user's email. Derive:

| Variable | Derivation | Example |
|----------|-----------|---------|
| `APP_NAME` | `{firstname}-{lastinitial}-booking-app` (max 26 chars) | `jaiwant-j-booking-app` |
| `DB_SCHEMA` | `APP_NAME` with hyphens replaced by underscores | `jaiwant_j_booking_app` |
| `REPO_ROOT` | `/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template` | |
| `APP_BASE` | `{REPO_ROOT}/apps_lakebase/{APP_NAME}` | |

Also set up the `write_file` helper using the Databricks SDK (same as prior steps).

---

### Step 2: Provision Lakebase Infrastructure (SDK — copy these cells)

> **Why this section exists:** `04-appkit-plugin-add/SKILL.md` documents **CLI / bundle** Lakebase flows (`databricks postgres …`, `databricks.yml`). It does **not** define Genie “Steps 3a–3d”. Without the cells below, Genie often pastes **obsolete** `w.database.create_database_instance(name=...)` and **hangs or errors**. Use **exactly** this sequence.

**Order:** ensure instance **AVAILABLE** → grant app SP **DATABRICKS_SUPERUSER** → discover default DB path on `production` branch → **merge** `postgres` resource on the app.

#### Step 2a — Database instance (Lakebase project / instance = `APP_NAME`)

Current SDK: `create_database_instance` takes a **`DatabaseInstance`** object (not `name=`). `get_database_instance` raises **`NotFound`** when the instance does not exist yet — that is **expected** on first run.

```python
from databricks.sdk.errors import NotFound
from databricks.sdk.service.database import DatabaseInstance

try:
    instance = w.database.get_database_instance(name=APP_NAME)
    print("Instance exists; state=", getattr(instance.state, "name", instance.state))
except NotFound:
    print("Creating database instance (long-running)...")
    instance = w.database.create_database_instance_and_wait(DatabaseInstance(name=APP_NAME))

# Wait until DNS is present (some regions fill read_write_dns after state AVAILABLE)
instance = w.database.get_database_instance(name=APP_NAME)
LAKEBASE_HOST = instance.read_write_dns or ""
print("read_write_dns:", LAKEBASE_HOST or "(empty until ready — re-get after ~1 min if needed)")
```

If `create_database_instance_and_wait` is missing, upgrade the SDK (`%pip install --upgrade databricks-sdk -q` + `restartPython`) and use `waiter = w.database.create_database_instance(DatabaseInstance(name=APP_NAME)); waiter.result()` per current docs.

#### Step 2b — Branch path and default database id

Use **`w.postgres.list_databases`** only — do **not** call **`w.postgres.create_database`** here (Genie often hits **`spec.role` empty**; default DB already exists). **`DB_SCHEMA`** is the Postgres schema name for later DDL; the binding path is **`dbs[0].name`** (`projects/.../databases/db-...`). Extended rationale and errors: **`troubleshooting_gc.md`** → *Setup Lakebase — extended notes*.

```python
branch_path = f"projects/{APP_NAME}/branches/production"
dbs = list(w.postgres.list_databases(parent=branch_path))
if not dbs:
    raise RuntimeError(
        "No databases on branch yet. Re-run this cell after instance is AVAILABLE, "
        "or wait ~30–60s for platform provisioning."
    )
db_path = dbs[0].name
print("branch_path:", branch_path)
print("database path for binding:", db_path)
```

#### Step 2c — Grant app service principal `DATABRICKS_SUPERUSER`

Use **`w.database.create_database_instance_role`** only — not **`w.postgres.create_role`** (wrong **`parent`** paths / incomplete **`Role`** spec). Retry **`DatabaseInstanceRole.name`**: numeric **`str(service_principal_id)`** first, then **`service_principal_client_id`**. Escape hatch and **`Identity not found`**: **`troubleshooting_gc.md`** → *Setup Lakebase — extended notes*.

```python
from databricks.sdk.service.database import (
    DatabaseInstanceRole,
    DatabaseInstanceRoleIdentityType,
    DatabaseInstanceRoleMembershipRole,
)

app0 = w.apps.get(name=APP_NAME)
sp_id = app0.service_principal_id
if sp_id is None:
    raise RuntimeError("App has no service_principal_id — create/wait for app first.")

def _grant(name: str) -> None:
    w.database.create_database_instance_role(
        APP_NAME,
        DatabaseInstanceRole(
            name=name,
            identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL,
            membership_role=DatabaseInstanceRoleMembershipRole.DATABRICKS_SUPERUSER,
        ),
    )

try:
    _grant(str(sp_id))
    print("Granted DATABRICKS_SUPERUSER (role name = numeric service_principal_id)")
except Exception as e1:
    cid = app0.service_principal_client_id
    if not cid:
        raise
    print("Retrying grant with service_principal_client_id (UUID) as role name:", e1)
    _grant(cid)
    print("Granted DATABRICKS_SUPERUSER (role name = service_principal_client_id UUID)")
```

#### Step 2d — Bind `postgres` resource on the app (merge existing resources)

Merge via **`app.as_dict()`** → dict **`resources`** (string **`permission`**: `"CAN_CONNECT_AND_CREATE"`) → **`App.from_dict(d)`** → **`w.apps.update`** — preserves other app fields and avoids **`permission` `.value`** errors. Details: **`troubleshooting_gc.md`** Step 2 error table.

```python
from databricks.sdk.service.apps import App

app1 = w.apps.get(name=APP_NAME)
d = app1.as_dict()
res = [x for x in (d.get("resources") or []) if x.get("name") != "postgres"]
res.append(
    {
        "name": "postgres",
        "postgres": {
            "branch": branch_path,
            "database": db_path,
            "permission": "CAN_CONNECT_AND_CREATE",
        },
    }
)
d["resources"] = res
w.apps.update(name=APP_NAME, app=App.from_dict(d))
print("Bound app.resources postgres → branch + database path")
```

#### Optional: UC `DatabaseCatalog` (skip unless your workspace requires it)

Some orgs require a Unity Catalog **`DatabaseCatalog`** linked to the instance. If **`list_databases`** already returns a default DB, you usually **skip** this. If platform docs require it, use `w.database.create_database_catalog(DatabaseCatalog(...))` with UC-legal **`name`**, `database_instance_name=APP_NAME`, and the target **`database_name`** — see SDK dataclass `DatabaseCatalog`. If the API returns “unimplemented” or you are unsure, **skip** and continue with the default `db_path` from Step 2b.

---

### Step 3: Lakebase boilerplate (SDK + skill)

Read `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` **Steps 2b–2c** and `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` (**`app.yaml` — Lakebase env section**, **`package.json`**).

- Merge **`LAKEBASE_ENDPOINT`** with **`valueFrom: postgres`** and **`DB_SCHEMA`** into `app.yaml` via `write_file()`.
- Ensure **`@databricks/lakebase`** is listed in `package.json` **`dependencies`** via `write_file()`.

> **Important:** Step 2 above creates the Lakebase project/database and binds the **`postgres`** resource. This step only updates **config files** — do **not** change `server/server.ts` yet (that is `wire_ui_to_lakebase_gc.md`).

---

### Step 4: Configure `app.yaml` and `package.json`

Ensure `package.json` has `@databricks/lakebase` in `dependencies` (not `devDependencies`).

Update `app.yaml` with Lakebase environment variables — see `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` Step 2c for the Lakebase `app.yaml` env pattern (`LAKEBASE_ENDPOINT` with `valueFrom: postgres`, `DB_SCHEMA` with your derived value).

> **CRITICAL:** Use `LAKEBASE_ENDPOINT` with `valueFrom: postgres` — NOT `DATABRICKS_LAKEBASE_DB` with `valueFrom: database`. AppKit's `lakebase()` plugin requires a `postgres`-type resource. Using the wrong type causes `ConfigurationError` at startup.

> **Do NOT set `PGHOST`, `PGPORT`, `PGDATABASE` manually** — the `lakebase()` plugin derives these from the `postgres` resource binding.

If `app.yaml` already has other entries, merge — do not overwrite.

---

### Step 5: Verify All Changes

1. **Read `package.json`** — confirm `@databricks/lakebase` is in `dependencies`
2. **Read `app.yaml`** — confirm `LAKEBASE_ENDPOINT` with `valueFrom: postgres` and `DB_SCHEMA` are set
3. **Read `app.ts`** — confirm it is **unchanged** (still uses `createApp({ plugins: [server()] })`)
4. **Check instance status** — `w.database.get_database_instance(name=APP_NAME)`; `state.name == "AVAILABLE"` (or print `state` if older SDK shape)
5. **Check resource binding** — `w.apps.get(name=APP_NAME)` resources includes a `postgres`-type resource:

```python
app = w.apps.get(name=APP_NAME)
for r in (app.resources or []):
    pg = r.postgres
    if pg:
        print(f"  ✓ Resource '{r.name}' → branch={pg.branch}, db={pg.database}")
    else:
        print(f"  ⚠ Resource '{r.name}' is NOT postgres type — AppKit will crash. Re-run Step 2d.")
```

---

### Checklist

- [ ] Lakebase instance created — state `AVAILABLE`
- [ ] Default DB path discovered via **`list_databases`** (full path like `.../databases/db-...`; **`DB_SCHEMA`** is only the Postgres schema name for DDL later — not the same string)
- [ ] App SP granted `DATABRICKS_SUPERUSER`
- [ ] App resource bound — `postgres`-type resource named `postgres` visible (NOT `database` type)
- [ ] `@databricks/lakebase` added to `package.json` `dependencies`
- [ ] `app.ts` is **unchanged** (still `createApp({ plugins: [server()] })`)
- [ ] `DB_SCHEMA` derived from `APP_NAME` (hyphens to underscores)
- [ ] `app.yaml` has `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA`
- [ ] `.vibecoding-state.md` updated with: `DB_SCHEMA`, `LAKEBASE_HOST`, instance state, SP IDs

**Previous step:** `one-ui-design-local.md` | **Next step:** `wire_ui_to_lakebase_gc.md`

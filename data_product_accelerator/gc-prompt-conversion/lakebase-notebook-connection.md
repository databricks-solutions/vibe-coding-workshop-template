# Lakebase Notebook Connection

Connect to a Lakebase PostgreSQL database from a Genie Code notebook using the Databricks SDK (`w.postgres`) and `psycopg`.

## Prerequisites

Run as **two separate cells** at the start of the notebook:

**Cell 1 — install packages** (always run this first):
```python
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
```

**Cell 2 — restart only if SDK was already imported**:
If the next cell raises `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'`, it means an older SDK version was already loaded. Run this cell, then re-run the setup and connection cells:
```python
dbutils.library.restartPython()
```
> After restart, re-run the pip install cell, then proceed — psycopg and the upgraded SDK will be available without another restart.

**Before the connection pattern:** run `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` so `APP_NAME`, `DB_SCHEMA`, `REPO_ROOT`, and `w` exist.

## Resolve Lakebase project id (`LAKEBASE_PROJECT_ID`)

The **Databricks App name** and **Lakebase project id** are usually the same string, but Genie Code / the apps workshop may use a different folder name (e.g. `jaiwant-jo-stayfindr`) than the formula-derived `APP_NAME` (e.g. `jaiwant-j-booking-app`). Endpoint discovery must use the **actual** project id.

After resolution:

- **`LAKEBASE_PROJECT_ID`** — short id (no `projects/` prefix), e.g. `jaiwant-jo-stayfindr`
- **`PG_SCHEMA`** — `LAKEBASE_PROJECT_ID.replace("-", "_")` — same rule as `app.yaml` `DB_SCHEMA` when the app folder matches the project (e.g. `jaiwant_jo_stayfindr`)

If you already know the project id, you may set **`LAKEBASE_PROJECT_ID = "your-project-id"`** in a cell before the connection block and skip auto-discovery.

## Connection Pattern

```python
import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ObjectType

w = WorkspaceClient()

BRANCH = "production"

def _endpoints_for(project_short_id: str):
    return list(w.postgres.list_endpoints(
        parent=f"projects/{project_short_id}/branches/{BRANCH}"
    ))

# --- 1) Resolve LAKEBASE_PROJECT_ID (short id, no "projects/" prefix) ---
try:
    eps = _endpoints_for(APP_NAME)
except Exception:
    # list_endpoints raises NotFound when projects/{APP_NAME} does not exist
    eps = []

if eps:
    LAKEBASE_PROJECT_ID = APP_NAME
else:
    apps_base = f"{REPO_ROOT}/apps_lakebase"
    candidates = []
    try:
        objs = list(w.workspace.list(path=apps_base))
    except Exception:
        objs = []
    for obj in objs:
        if getattr(obj, "object_type", None) != ObjectType.DIRECTORY:
            continue
        d = obj.path.rstrip("/").split("/")[-1]
        try:
            ep = _endpoints_for(d)
        except Exception:
            ep = []
        if ep:
            candidates.append((d, ep))

    if not candidates:
        for p in w.postgres.list_projects():
            short = (p.name or "").split("/")[-1]
            if not short:
                continue
            try:
                ep = _endpoints_for(short)
            except Exception:
                ep = []
            if ep:
                candidates.append((short, ep))

    if len(candidates) == 1:
        LAKEBASE_PROJECT_ID, eps = candidates[0]
    elif len(candidates) > 1:
        match_app = next((c for c in candidates if c[0] == APP_NAME), None)
        if match_app:
            LAKEBASE_PROJECT_ID, eps = match_app
        else:
            api_suffixes = {
                (p.name or "").split("/")[-1]
                for p in w.postgres.list_projects()
                if p.name and "/" in p.name
            }
            scored = [c for c in candidates if c[0] in api_suffixes]
            if len(scored) == 1:
                LAKEBASE_PROJECT_ID, eps = scored[0]
            else:
                ids = [c[0] for c in candidates]
                raise RuntimeError(
                    f"Multiple app directories under {apps_base} have Lakebase endpoints: {ids}. "
                    f"Set LAKEBASE_PROJECT_ID to one of these ids before the connection block, "
                    f"or remove stale directories. Formula APP_NAME was {APP_NAME!r}."
                )
    else:
        raise RuntimeError(
            f"No endpoints for projects/{APP_NAME}/branches/{BRANCH}, and no app folder "
            f"under {apps_base} with a Lakebase project. Run the apps_lakebase workshop "
            f"(setup_lakebase_gc.md) or set LAKEBASE_PROJECT_ID manually."
        )

PG_SCHEMA = LAKEBASE_PROJECT_ID.replace("-", "_")
print(f"LAKEBASE_PROJECT_ID: {LAKEBASE_PROJECT_ID}")
print(f"PG_SCHEMA:           {PG_SCHEMA}")

# --- 2) Dynamic endpoint discovery ---
ENDPOINT_NAME = eps[0].name
print(f"Endpoint: {ENDPOINT_NAME}")

# --- 3) Host and credentials ---
endpoint = w.postgres.get_endpoint(name=ENDPOINT_NAME)
host = endpoint.status.hosts.host
print(f"Lakebase host: {host}")

cred = w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)
username = w.current_user.me().user_name

# --- 4) Connect via psycopg (Lakebase Autoscaling) ---
# Use dbname=databricks_postgres. App DDL creates tables in schema PG_SCHEMA
# (same naming as DB_SCHEMA in app.yaml when project id matches the app folder).
conn_string = (
    f"host={host} "
    f"dbname=databricks_postgres "
    f"user={username} "
    f"password={cred.token} "
    f"sslmode=require"
)

with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        print(f"Connected: {cur.fetchone()[0][:60]}...")
```

## Key Details

| Item | Value |
|------|-------|
| API | `w.postgres` (Lakebase Autoscaling) |
| Project id | **`LAKEBASE_PROJECT_ID`** — resolved from `APP_NAME` or from `REPO_ROOT/apps_lakebase/*` (see above) |
| Endpoint discovery | `w.postgres.list_endpoints(parent=f"projects/{LAKEBASE_PROJECT_ID}/branches/production")` |
| Credential | `w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)` — tokens last ~1 hour |
| Database name (`dbname`) | **`databricks_postgres`** — the managed Postgres database for the branch |
| Schema for app tables / `information_schema` | **`PG_SCHEMA`** = `LAKEBASE_PROJECT_ID.replace("-", "_")` — filter `WHERE table_schema = PG_SCHEMA` |
| `APP_NAME` / `DB_SCHEMA` from workshop-variables | Still used for **job names** and **paths**; they may differ from `LAKEBASE_PROJECT_ID` / `PG_SCHEMA` after a renamed app folder |
| SSL | Always `sslmode=require` |
| Bronze `clone_from_source` job notebooks | Must copy the **resolution + connection** block above verbatim (including per-directory `try`/`except` around `_endpoints_for`) — do not assume `projects/{APP_NAME}` exists |
| Bronze clone: PG `numeric` → Spark | Coordinate columns (`lat`, `lng`, `latitude`, `longitude`, `lon`): use **`DoubleType()`** and **`float`** values in rows. Other `numeric`: **`DecimalType`** with enough precision or explicit `(p,s)` from `information_schema`. Avoid **`DecimalType(18,2)`** for lat/lng — Arrow raises **`ArrowInvalid` / Rescaling Decimal128** |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `'WorkspaceClient' object has no attribute 'postgres'` | SDK too old | Run `%pip install --upgrade databricks-sdk -q` and restart kernel |
| `endpoint id not found` | Wrong endpoint name (e.g. `ep-primary`) | Use dynamic discovery via `list_endpoints()` — full `ENDPOINT_NAME` comes from the API |
| `list_endpoints` empty for `projects/{APP_NAME}/...` or **`NotFound`** for that parent | **Lakebase project id ≠ formula `APP_NAME`** (e.g. StayFindr app folder `jaiwant-jo-stayfindr`); API may **raise** instead of returning `[]` | Wrap `_endpoints_for(APP_NAME)` in `try`/`except`, then use the resolution block above (scan `apps_lakebase/` with **per-directory** `try`/`except`) or set **`LAKEBASE_PROJECT_ID`** manually |
| `FATAL: database "..." does not exist` | Wrong **`dbname`** — typo, or mistakenly using **`DB_SCHEMA`** / another string as the database name | Use exactly **`databricks_postgres`** for Lakebase Autoscaling (unless your admin documents a different branch database) |
| `Multiple app directories...` RuntimeError | Several folders under `apps_lakebase/` each have endpoints | Set **`LAKEBASE_PROJECT_ID`** to the correct short id, or remove stale app directories |
| Connected but **0 rows** from `information_schema.columns` | Wrong **`table_schema`** filter, or schema empty (app never deployed DDL) | Use **`dbname=databricks_postgres`** and **`WHERE table_schema = PG_SCHEMA`** with resolved `PG_SCHEMA`. Deploy the AppKit app once so DDL creates the schema |
| `password authentication failed` | Token expired | Call `generate_database_credential()` again before connecting |
| `ArrowInvalid` / `Rescaling Decimal128 value would cause data loss` when building Bronze from psycopg rows | Fixed **`DecimalType`** too narrow for **`numeric`** lat/lng | Use **`DoubleType`** + **`float`** for coordinate column names; see **Key Details** row “Bronze clone: PG `numeric` → Spark” |

## Common Queries

Use **`PG_SCHEMA`** (from the connection block) in filters. Qualify tables as `"SchemaName".table_name` if needed.

```sql
-- List all tables
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = '{PG_SCHEMA}'
ORDER BY table_name;

-- Full column metadata (for data dictionaries)
SELECT table_catalog, table_schema, table_name, column_name,
       ordinal_position, column_default, is_nullable, data_type,
       character_maximum_length, numeric_precision, numeric_scale, udt_name
FROM information_schema.columns
WHERE table_schema = '{PG_SCHEMA}'
ORDER BY table_name, ordinal_position;

-- Sample data (replace listings with your table name)
SELECT * FROM {PG_SCHEMA}.listings LIMIT 10;

-- Row counts
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = '{PG_SCHEMA}'
ORDER BY relname;

-- Foreign key relationships
SELECT tc.table_name, kcu.column_name,
       ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = '{PG_SCHEMA}';
```

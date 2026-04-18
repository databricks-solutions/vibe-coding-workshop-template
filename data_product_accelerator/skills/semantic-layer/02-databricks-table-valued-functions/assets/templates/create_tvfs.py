# Databricks notebook source
# ===========================================================================
# CREATE TABLE-VALUED FUNCTIONS (Python notebook — deployed via Asset Bundle)
# ---------------------------------------------------------------------------
# Why Python (not sql_task)?
#   TVF DDL schema-qualifies function names with ${catalog}.${gold_schema}.
#   `sql_task.parameters` are bind parameters (`:param`) that substitute VALUES,
#   not identifiers — they cannot rewrite function names. Python does a plain
#   string substitution BEFORE calling spark.sql().
#
# Runtime guarantees:
#   - Uses the canonical `rsplit('/src/', 1)[0]` pattern for bundle root.
#   - Loads the SQL file via `bundle_path(...)`, NEVER via `__file__`
#     (`__file__` is undefined inside notebook cells and raises NameError).
#   - Fails LOUD with RuntimeError on any CREATE failure — never calls
#     `sys.exit(0)` to report a failure (exit 0 = "success" to Databricks Jobs
#     and silently hides broken deploys).
# ===========================================================================

import sys
from pathlib import Path

# --- Bootstrap: prepend bundle root to sys.path so the shared helper imports. ---
try:
    _nb = (
        dbutils.notebook.entry_point.getDbutils()
        .notebook().getContext().notebookPath().get()
    )
    _root = "/Workspace" + str(_nb).rsplit("/src/", 1)[0]
    if _root not in sys.path:
        sys.path.insert(0, _root)
except Exception:
    pass  # Local execution

from src.common._notebook_paths import (
    ensure_bundle_root_on_path,
    bundle_path,
    fail_loud,
)

BUNDLE_ROOT = ensure_bundle_root_on_path(verbose=True)

# COMMAND ----------

# --- Parameters ---
dbutils.widgets.text("catalog", "")
dbutils.widgets.text("gold_schema", "")
dbutils.widgets.text(
    "sql_file",
    "src/{project_name}_semantic/table_valued_functions.sql",
)

catalog = dbutils.widgets.get("catalog").strip()
gold_schema = dbutils.widgets.get("gold_schema").strip()
sql_file_rel = dbutils.widgets.get("sql_file").strip()

missing = [
    name for name, val in [
        ("catalog", catalog),
        ("gold_schema", gold_schema),
        ("sql_file", sql_file_rel),
    ] if not val
]
if missing:
    fail_loud(f"Missing required widget values: {', '.join(missing)}")

sql_path = bundle_path(*sql_file_rel.split("/"))
if not sql_path.exists():
    fail_loud(f"SQL file not found: {sql_path}")

print(f"Loading TVF SQL from: {sql_path}")
print(f"  catalog     = {catalog}")
print(f"  gold_schema = {gold_schema}")

# COMMAND ----------

raw_sql = sql_path.read_text()
rendered_sql = (
    raw_sql
    .replace("${catalog}", catalog)
    .replace("${gold_schema}", gold_schema)
)

# Split on bare `;` statements. Strip comments-only segments.
statements = [s.strip() for s in rendered_sql.split(";") if s.strip()]
print(f"Loaded {len(statements)} TVF DDL statement(s).")

# COMMAND ----------

success, failed = [], []
for idx, stmt in enumerate(statements, start=1):
    preview = stmt.splitlines()[0][:120]
    try:
        spark.sql(stmt)
        success.append(preview)
        print(f"  [{idx}/{len(statements)}] ✓ {preview}")
    except Exception as e:  # noqa: BLE001
        failed.append({"preview": preview, "error": str(e)})
        print(f"  [{idx}/{len(statements)}] ✗ {preview}\n    ERROR: {e}")

print("=" * 80)
print(f"Created {len(success)} / {len(statements)} TVFs.")

if failed:
    detail = "\n".join(f"  - {f['preview']} :: {f['error']}" for f in failed)
    fail_loud(
        f"Failed to create {len(failed)} TVF(s):\n{detail}"
    )

print("✅ All TVFs created successfully.")

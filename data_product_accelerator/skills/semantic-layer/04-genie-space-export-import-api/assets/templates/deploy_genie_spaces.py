# Databricks notebook source
# ===========================================================================
# PATH SETUP FOR ASSET BUNDLE IMPORTS
# ===========================================================================
# Enables imports from src modules when deployed via Databricks Asset Bundles.
# Reference: https://docs.databricks.com/aws/en/notebooks/share-code
import sys
import os

try:
    _notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    _bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
    if _bundle_root not in sys.path:
        sys.path.insert(0, _bundle_root)
        print(f"Added bundle root to sys.path: {_bundle_root}")
except Exception as e:
    print(f"Path setup skipped (local execution): {e}")
# ===========================================================================
"""
Deploy Genie Spaces from JSON configuration files via REST API.

This notebook is designed for Databricks Asset Bundle deployment using notebook_task.
Parameters are received via dbutils.widgets.get() (not argparse).

Key features:
- Recursive variable substitution (handles nested ${catalog}/${gold_schema})
- Array sorting (API requires sorted arrays)
- Pre-flight JSON validation
- Idempotent deployment (update-or-create pattern via space ID variables)
- Proper serialized_space extraction (handles wrapped vs raw format)
- PATCH without title (avoids " (updated)" suffix mutation)

For CLI/CI usage, use scripts/import_genie_space.py instead.
"""
# COMMAND ----------

import json
import re
import uuid
import requests
from pathlib import Path

# COMMAND ----------

# Parameters via dbutils.widgets (set by notebook_task base_parameters)
catalog = dbutils.widgets.get("catalog")
gold_schema = dbutils.widgets.get("gold_schema")
config_dir = dbutils.widgets.get("config_dir")
warehouse_id = dbutils.widgets.get("warehouse_id")

print(f"Catalog: {catalog}")
print(f"Gold Schema: {gold_schema}")
print(f"Config Dir: {config_dir}")
print(f"Warehouse ID: {warehouse_id}")

# COMMAND ----------

# Derive workspace host and token from runtime context
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
host = ctx.apiUrl().get()
token = ctx.apiToken().get()

print(f"Workspace: {host}")

# COMMAND ----------

# Genie Space metadata: maps config filename stems to space ID widget names
# Populate this dict with your Genie Space configs.
# Example: {"revenue_analytics": "genie_space_id_revenue_analytics"}
GENIE_SPACE_METADATA = {}

# COMMAND ----------


def generate_id() -> str:
    """Generate a Genie Space compatible ID (32 hex chars, no dashes)."""
    return uuid.uuid4().hex


def process_json_values(obj, variables: dict):
    """Recursively substitute ${var} patterns in all string values."""
    if isinstance(obj, str):
        for key, value in variables.items():
            obj = obj.replace(f"${{{key}}}", value)
        return obj
    elif isinstance(obj, dict):
        return {k: process_json_values(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_json_values(item, variables) for item in obj]
    return obj


def sort_all_arrays(space: dict) -> dict:
    """Sort all arrays in Genie Space JSON by their API-required sort keys."""
    if "tables" in space:
        space["tables"] = sorted(
            space["tables"], key=lambda x: x.get("table_name", "")
        )
    if "materialized_views" in space:
        space["materialized_views"] = sorted(
            space["materialized_views"],
            key=lambda x: x.get("materialized_view_name", ""),
        )
    if "sql_functions" in space:
        space["sql_functions"] = sorted(
            space["sql_functions"], key=lambda x: x.get("function_name", "")
        )
    if "example_question_sqls" in space:
        space["example_question_sqls"] = sorted(
            space["example_question_sqls"],
            key=lambda x: (
                x.get("question", [""])[0]
                if isinstance(x.get("question"), list)
                else x.get("question", "")
            ),
        )
    return space


_UUID4_HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def validate_genie_json_structure(space: dict) -> list[str]:
    """Pre-flight validation of Genie Space JSON structure. Returns list of errors."""
    errors = []

    def _check_id(path: str, value):
        if not isinstance(value, str) or not _UUID4_HEX_PATTERN.match(value):
            errors.append(f"{path}: ID must be 32-char hex (uuid4.hex), got: {value!r}")

    if "id" in space:
        _check_id("space.id", space["id"])

    for arr_name, id_field in [
        ("tables", "id"),
        ("sql_functions", "id"),
        ("materialized_views", "id"),
        ("example_question_sqls", "id"),
    ]:
        for i, item in enumerate(space.get(arr_name, [])):
            if id_field in item:
                _check_id(f"{arr_name}[{i}].{id_field}", item[id_field])

    string_array_fields = [
        ("example_question_sqls", "question"),
        ("tables", "description"),
        ("materialized_views", "description"),
        ("sql_functions", "description"),
    ]
    for arr_name, field in string_array_fields:
        for i, item in enumerate(space.get(arr_name, [])):
            val = item.get(field)
            if val is not None and not isinstance(val, list):
                errors.append(
                    f"{arr_name}[{i}].{field}: must be array, got {type(val).__name__}"
                )

    for i, q in enumerate(space.get("example_question_sqls", [])):
        for j, ans in enumerate(q.get("answer", [])):
            content = ans.get("content")
            if content is not None and not isinstance(content, list):
                errors.append(
                    f"example_question_sqls[{i}].answer[{j}].content: must be array"
                )

    if "expected_sql" in space:
        errors.append(
            "Top-level 'expected_sql' field is invalid. "
            "Use answer: [{format: 'SQL', content: ['SELECT ...']}] in benchmarks."
        )

    return errors


def extract_space_config(raw_config: dict) -> dict:
    """Extract space configuration, handling both wrapped and raw formats."""
    if "serialized_space" in raw_config:
        serialized = raw_config["serialized_space"]
        if isinstance(serialized, str):
            return json.loads(serialized)
        return serialized
    if "space" in raw_config and "serialized_space" in raw_config.get("space", {}):
        serialized = raw_config["space"]["serialized_space"]
        if isinstance(serialized, str):
            return json.loads(serialized)
        return serialized
    return raw_config


# COMMAND ----------


def deploy_space(
    host: str,
    token: str,
    title: str,
    description: str,
    warehouse_id: str,
    space_config: dict,
    space_id: str = "",
) -> dict:
    """Deploy a Genie Space using update-or-create pattern.

    Args:
        space_id: If provided, PATCHes existing space. If empty, POSTs new space.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    serialized = json.dumps(space_config)

    if space_id:
        # UPDATE existing space — omit title to avoid " (updated)" suffix
        payload = {
            "description": description,
            "warehouse_id": warehouse_id,
            "serialized_space": serialized,
        }
        url = f"{host}/api/2.0/genie/spaces/{space_id}"
        response = requests.patch(url, headers=headers, json=payload)
        action = "Updated"
    else:
        payload = {
            "title": title,
            "description": description,
            "warehouse_id": warehouse_id,
            "serialized_space": serialized,
        }
        url = f"{host}/api/2.0/genie/spaces"
        response = requests.post(url, headers=headers, json=payload)
        action = "Created"

    response.raise_for_status()
    result = response.json()

    result_id = result.get("space", {}).get("id") or result.get("space_id", "unknown")
    print(f"{action} Genie Space: {result_id} ({title})")

    return result


# COMMAND ----------

# Resolve config directory path within the bundle workspace
_notebook_path = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
_bundle_root = "/Workspace" + str(_notebook_path).rsplit("/src/", 1)[0]
config_path = Path(f"{_bundle_root}/{config_dir}")

print(f"Looking for JSON configs in: {config_path}")

json_files = sorted(config_path.glob("*.json"))
if not json_files:
    print(f"No JSON config files found in {config_path}")
    dbutils.notebook.exit("No configs found")

print(f"Found {len(json_files)} Genie Space config(s): {[f.name for f in json_files]}")

# COMMAND ----------

variables = {
    "catalog": catalog,
    "gold_schema": gold_schema,
}

results = []
errors_all = []

for config_file in json_files:
    print(f"\n{'='*60}")
    print(f"Processing: {config_file.name}")
    print(f"{'='*60}")

    with open(config_file, "r") as f:
        raw_config = json.load(f)

    space_config = extract_space_config(raw_config)
    space_config = process_json_values(space_config, variables)

    validation_errors = validate_genie_json_structure(space_config)
    if validation_errors:
        print(f"⚠️ Validation errors in {config_file.name}:")
        for err in validation_errors:
            print(f"  - {err}")
        errors_all.extend(validation_errors)

    space_config = sort_all_arrays(space_config)

    title = raw_config.get("title") or config_file.stem.replace("_", " ").title()
    desc = raw_config.get("description", f"Genie Space from {config_file.name}")
    title = process_json_values(title, variables)
    desc = process_json_values(desc, variables)

    # Resolve space ID from widget (for idempotent update-or-create)
    space_id_widget = GENIE_SPACE_METADATA.get(config_file.stem, "")
    space_id = ""
    if space_id_widget:
        try:
            space_id = dbutils.widgets.get(space_id_widget)
        except Exception:
            space_id = ""

    result = deploy_space(
        host=host,
        token=token,
        title=title,
        description=desc,
        warehouse_id=warehouse_id,
        space_config=space_config,
        space_id=space_id,
    )
    results.append({"title": title, "result": result, "config_file": config_file.name})

# COMMAND ----------

print(f"\n{'='*60}")
print(f"DEPLOYMENT SUMMARY")
print(f"{'='*60}")
print(f"Total Genie Spaces processed: {len(results)}")
print(f"Validation errors: {len(errors_all)}")

for r in results:
    result_data = r["result"]
    sid = (
        result_data.get("space", {}).get("id")
        or result_data.get("space_id", "unknown")
    )
    print(f"  - {r['title']}: {sid}")
    stem = Path(r["config_file"]).stem
    print(f"    → Set variable: genie_space_id_{stem} = {sid}")

if errors_all:
    print(f"\n⚠️ {len(errors_all)} validation error(s) detected. Review above.")

dbutils.notebook.exit(
    json.dumps({"spaces_deployed": len(results), "validation_errors": len(errors_all)})
)

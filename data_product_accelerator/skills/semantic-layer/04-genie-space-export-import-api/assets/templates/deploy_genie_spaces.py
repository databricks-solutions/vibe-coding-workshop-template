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


def sort_all_arrays(config: dict) -> dict:
    """Sort all arrays in the Genie Space JSON — API rejects unsorted data.

    Canonical sort keys per 04-genie-space-export-import-api/SKILL.md §8:
      - data_sources.tables             → identifier
      - data_sources.metric_views       → identifier
      - instructions.sql_functions      → (id, identifier)
      - instructions.text_instructions  → id
      - instructions.example_question_sqls → id
      - instructions.sql_snippets.{measures,filters,expressions} → id
      - config.sample_questions         → id
      - benchmarks.questions            → id
    """
    if "data_sources" in config:
        for key in ["tables", "metric_views"]:
            if key in config["data_sources"]:
                config["data_sources"][key] = sorted(
                    config["data_sources"][key],
                    key=lambda x: x.get("identifier", ""),
                )
    if "instructions" in config:
        if "sql_functions" in config["instructions"]:
            config["instructions"]["sql_functions"] = sorted(
                config["instructions"]["sql_functions"],
                key=lambda x: (x.get("id", ""), x.get("identifier", "")),
            )
        for key in ["text_instructions", "example_question_sqls"]:
            if key in config["instructions"]:
                config["instructions"][key] = sorted(
                    config["instructions"][key],
                    key=lambda x: x.get("id", ""),
                )
        if "sql_snippets" in config["instructions"]:
            for key in ["measures", "filters", "expressions"]:
                if key in config["instructions"]["sql_snippets"]:
                    config["instructions"]["sql_snippets"][key] = sorted(
                        config["instructions"]["sql_snippets"][key],
                        key=lambda x: x.get("id", ""),
                    )
    if "config" in config and "sample_questions" in config["config"]:
        config["config"]["sample_questions"] = sorted(
            config["config"]["sample_questions"],
            key=lambda x: x.get("id", ""),
        )
    if "benchmarks" in config and "questions" in config["benchmarks"]:
        config["benchmarks"]["questions"] = sorted(
            config["benchmarks"]["questions"],
            key=lambda x: x.get("id", ""),
        )
    return config


_UUID4_HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def validate_genie_json_structure(space: dict) -> list[str]:
    """Pre-flight validation of Genie Space JSON structure. Returns list of errors.

    NOTE: This validator walks a flat-schema shape (top-level `tables`,
    `materialized_views`, `sql_functions`, `example_question_sqls`). Real
    exported configs use the nested schema documented in SKILL.md §4
    (ID Generation) and §7 (Field Validation Rules) — see
    `data_product_accelerator/skills/semantic-layer/04-genie-space-export-import-api/SKILL.md`.
    For nested-schema inputs, the loops below are effectively no-ops and
    the authoritative rules in those SKILL.md sections supersede the
    assertions here. A test-backed update to this validator is tracked
    separately; do not treat a clean result here as full coverage.
    """
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


def _assert_sql_arrays(space: dict) -> None:
    """
    Enforce serialized_space invariants BEFORE POST/PATCH.

    This is the authoritative fail-loud validator — it checks the #1 silent
    failure (sql field submitted as a bare string instead of List[str]) plus
    deploy-time invariants (version=2, concrete warehouse id, sorted data
    sources, uuid4.hex ids, 50-entry limits). See the invariants table in
    `data_product_accelerator/skills/semantic-layer/04-genie-space-export-import-api/SKILL.md`.

    Raises RuntimeError on the first violation. Never logs-and-continues.
    """
    errors: list = []

    if space.get("version") != 2:
        errors.append(f"version must be exactly 2 (got {space.get('version')!r})")

    cfg = space.get("config") or {}
    if not isinstance(cfg.get("title"), str) or not cfg.get("title"):
        errors.append("config.title must be a non-empty string")
    if not isinstance(cfg.get("description"), str) or not cfg.get("description"):
        errors.append("config.description must be a non-empty string")
    wh = cfg.get("semantic_warehouse_id")
    if not isinstance(wh, str) or not re.match(r"^[0-9a-f]{16,}$", wh or ""):
        errors.append(
            "config.semantic_warehouse_id must be a concrete deploy-time warehouse id; "
            f"got {wh!r}. Template placeholders are never acceptable."
        )

    ds = space.get("data_sources") or {}
    for key, name_field in [("tables", "table_full_name"), ("metric_views", "metric_view_full_name")]:
        items = ds.get(key) or []
        if not isinstance(items, list):
            errors.append(f"data_sources.{key} must be a list")
            continue
        names = [it.get(name_field, "") for it in items]
        if names != sorted(names):
            errors.append(f"data_sources.{key} must be sorted by {name_field}")
        for it in items:
            _id = it.get("id", "")
            if not (isinstance(_id, str) and _UUID4_HEX_PATTERN.match(_id)):
                errors.append(f"data_sources.{key} entry id must be uuid4.hex: {it}")

    def _check_sql_list(path: str, entries):
        if entries is None:
            return
        if not isinstance(entries, list):
            errors.append(f"{path} must be a list (got {type(entries).__name__})")
            return
        for idx, it in enumerate(entries):
            if not isinstance(it, dict):
                errors.append(f"{path}[{idx}] must be an object")
                continue
            _id = it.get("id", "")
            if not (isinstance(_id, str) and _UUID4_HEX_PATTERN.match(_id)):
                errors.append(f"{path}[{idx}].id must be uuid4.hex (32 hex chars)")
            sql_field = it.get("sql")
            if sql_field is None:
                continue
            if not isinstance(sql_field, list):
                errors.append(
                    f"{path}[{idx}].sql must be List[str] — got {type(sql_field).__name__}. "
                    "This is the #1 silent-failure: the API accepts a bare string but the "
                    'resulting space has broken example queries. Wrap SQL in ["..."].'
                )
                continue
            for sidx, s in enumerate(sql_field):
                if not isinstance(s, str) or not s.strip():
                    errors.append(f"{path}[{idx}].sql[{sidx}] must be a non-empty string")

    instr = space.get("instructions") or {}
    _check_sql_list("instructions.sql_functions", instr.get("sql_functions"))
    _check_sql_list("instructions.sample_queries", instr.get("sample_queries"))
    _check_sql_list("benchmarks.questions", (space.get("benchmarks") or {}).get("questions"))

    if len(instr.get("sql_functions") or []) > 50:
        errors.append("instructions.sql_functions exceeds 50-entry limit")
    if len((space.get("benchmarks") or {}).get("questions") or []) > 50:
        errors.append("benchmarks.questions exceeds 50-entry limit")

    gi = instr.get("general_instructions")
    if gi is not None:
        if not isinstance(gi, list) or not all(isinstance(x, str) for x in gi):
            errors.append("instructions.general_instructions must be List[str]")

    if errors:
        joined = "\n  - ".join(errors)
        raise RuntimeError(
            f"serialized_space validation failed — refusing to POST/PATCH:\n  - {joined}"
        )


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

    # Required root field: the ExportConverter rejects version 0.
    # See 04-genie-space-export-import-api/SKILL.md "Required Root Field".
    space_config.setdefault("version", 2)

    # Stamp the concrete deploy-time warehouse id into serialized_space.config so
    # the embedded invariant matches the POST envelope's warehouse_id.
    # See SKILL.md "Required `serialized_space` Invariants" and Action S10.
    cfg = space_config.setdefault("config", {})
    cfg["semantic_warehouse_id"] = warehouse_id
    cfg.setdefault("title", title)
    cfg.setdefault("description", description)

    # FAIL LOUD before POST/PATCH — never log-and-continue on structural defects.
    _assert_sql_arrays(space_config)

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

print("\n" + "=" * 70)
print("[ACTION REQUIRED] Copy the YAML below into databricks.yml under `variables:`")
print("to persist the space_id across runs. This converts the next deploy from")
print("POST (create) to PATCH (update) — the idempotent update-or-create path.")
print("=" * 70)
print("\nvariables:")
for r in results:
    result_data = r["result"]
    sid = (
        result_data.get("space", {}).get("id")
        or result_data.get("space_id", "unknown")
    )
    stem = Path(r["config_file"]).stem
    var_name = f"genie_space_id_{stem}"
    print(f"  {var_name}:")
    print(f"    description: 'Persisted Genie Space id for {r[\"title\"]!s} (do NOT edit)'")
    print(f"    default: '{sid}'")
print()
print("After pasting, re-run `databricks bundle deploy -t <target>` so the workspace")
print("copy of databricks.yml reflects the new ids. Subsequent runs of this notebook")
print("will PATCH the existing space instead of creating a new one — avoiding")
print("duplicate Genie Spaces in the workspace.\n")

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

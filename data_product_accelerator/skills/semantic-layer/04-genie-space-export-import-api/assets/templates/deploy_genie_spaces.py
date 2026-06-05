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
    """Non-fatal pre-flight reporter — SUPERSEDED by `_assert_sql_arrays`.

    The canonical v3.7.0 validator (`_assert_sql_arrays` below) is the
    authoritative, fail-loud check (run inside `deploy_space` before every
    POST/PATCH). This wrapper runs the SAME nested-schema checks non-fatally so
    the deploy summary can list structural issues up front. The previous body
    walked a deprecated flat schema (top-level `tables`/`materialized_views`,
    `id` on data sources) that contradicts the live API; it is removed.
    Schema reference:
    data_product_accelerator/skills/semantic-layer/04-genie-space-export-import-api/SKILL.md
    """
    try:
        _assert_sql_arrays(sort_all_arrays(space))
    except RuntimeError as exc:
        return [str(exc)]
    return []


def _assert_sql_arrays(space: dict) -> None:
    """
    Validate serialized_space invariants before POST / PATCH (canonical v3.7.0).

    Authoritative fail-loud validator. Raises RuntimeError on the first batch of
    violations — never logs-and-continues. Reconciled with the live
    getspace/createspace/updatespace API and the invariants table in
    `data_product_accelerator/skills/semantic-layer/04-genie-space-export-import-api/SKILL.md`.

    Enforces:
      - data_sources.tables / metric_views entries use `identifier` only (NO `id`;
        the API rejects `id` with `Cannot find field: id`).
      - instructions.sql_functions entries: {id, identifier} only.
      - instructions.example_question_sqls entries: {id, question: List[str], sql: List[str]}.
      - benchmarks.questions[].answer[].content must be List[str] (SQL lives there,
        not as a top-level `sql` field).
    """
    errors: list = []

    def _is_uuid_hex(value) -> bool:
        return isinstance(value, str) and bool(_UUID4_HEX_PATTERN.match(value))

    if space.get("version") != 2:
        errors.append("serialized_space.version must be exactly 2 (got %r)" % space.get("version"))

    cfg = space.get("config") or {}
    if not isinstance(cfg.get("title"), str) or not cfg.get("title"):
        errors.append("config.title must be a non-empty string")
    if not isinstance(cfg.get("description"), str) or not cfg.get("description"):
        errors.append("config.description must be a non-empty string")

    wh = cfg.get("semantic_warehouse_id")
    if not isinstance(wh, str) or not re.match(r"^[0-9a-f]{16,}$", wh or ""):
        errors.append(
            "config.semantic_warehouse_id must be a concrete warehouse id baked at deploy time; "
            f"got {wh!r}. Template placeholders like '${{warehouse_id}}' are never acceptable."
        )

    # Data sources — sorted by `identifier`, NEVER include `id` on these entries.
    ds = space.get("data_sources") or {}
    for key in ("tables", "metric_views"):
        items = ds.get(key) or []
        if not isinstance(items, list):
            errors.append(f"data_sources.{key} must be a list")
            continue
        idents = [it.get("identifier", "") for it in items]
        if idents != sorted(idents):
            errors.append(f"data_sources.{key} must be sorted by identifier (got {idents})")
        for it in items:
            if "id" in it:
                errors.append(
                    f"data_sources.{key} entry MUST NOT include `id` — the API rejects with "
                    f"`Cannot find field: id`. Use only `identifier` and optional `description`. Got: {it}"
                )
            ident = it.get("identifier")
            if not isinstance(ident, str) or ident.count(".") != 2:
                errors.append(
                    f"data_sources.{key} entry `identifier` must be 'catalog.schema.name': {it}"
                )

    instr = space.get("instructions") or {}

    # instructions.sql_functions — {id, identifier} only.
    sqlfns = instr.get("sql_functions") or []
    if not isinstance(sqlfns, list):
        errors.append("instructions.sql_functions must be a list")
    else:
        for idx, it in enumerate(sqlfns):
            if not isinstance(it, dict):
                errors.append(f"instructions.sql_functions[{idx}] must be an object")
                continue
            if not _is_uuid_hex(it.get("id")):
                errors.append(f"instructions.sql_functions[{idx}].id must be uuid4.hex (32 hex chars)")
            ident = it.get("identifier")
            if not isinstance(ident, str) or ident.count(".") != 2:
                errors.append(
                    f"instructions.sql_functions[{idx}].identifier must be 'catalog.schema.fn_name'"
                )

    # instructions.example_question_sqls — {id, question: List[str], sql: List[str]}.
    eqs = instr.get("example_question_sqls") or []
    if not isinstance(eqs, list):
        errors.append("instructions.example_question_sqls must be a list")
    else:
        for idx, it in enumerate(eqs):
            if not isinstance(it, dict):
                errors.append(f"instructions.example_question_sqls[{idx}] must be an object")
                continue
            if not _is_uuid_hex(it.get("id")):
                errors.append(f"instructions.example_question_sqls[{idx}].id must be uuid4.hex")
            for arr_field in ("question", "sql"):
                arr = it.get(arr_field)
                if not isinstance(arr, list) or not all(isinstance(s, str) and s.strip() for s in arr):
                    errors.append(
                        f"instructions.example_question_sqls[{idx}].{arr_field} must be a non-empty "
                        f"List[str] — single strings cause silent breakage. Wrap as [\"...\"]."
                    )

    # benchmarks.questions — SQL lives inside answer[].content, NOT a top-level sql field.
    bench = (space.get("benchmarks") or {}).get("questions") or []
    if not isinstance(bench, list):
        errors.append("benchmarks.questions must be a list")
    else:
        for idx, it in enumerate(bench):
            if not isinstance(it, dict):
                errors.append(f"benchmarks.questions[{idx}] must be an object")
                continue
            if not _is_uuid_hex(it.get("id")):
                errors.append(f"benchmarks.questions[{idx}].id must be uuid4.hex")
            q = it.get("question")
            if not isinstance(q, list) or not all(isinstance(s, str) and s.strip() for s in q):
                errors.append(f"benchmarks.questions[{idx}].question must be List[str]")
            answers = it.get("answer") or []
            if not isinstance(answers, list):
                errors.append(f"benchmarks.questions[{idx}].answer must be a list")
                continue
            for aidx, ans in enumerate(answers):
                if not isinstance(ans, dict):
                    errors.append(f"benchmarks.questions[{idx}].answer[{aidx}] must be an object")
                    continue
                if ans.get("format") not in ("SQL", "INSTRUCTIONS"):
                    errors.append(
                        f"benchmarks.questions[{idx}].answer[{aidx}].format must be 'SQL' or 'INSTRUCTIONS'"
                    )
                content = ans.get("content")
                if not isinstance(content, list) or not all(isinstance(s, str) and s.strip() for s in content):
                    errors.append(
                        f"benchmarks.questions[{idx}].answer[{aidx}].content must be List[str] — "
                        f"this is the #1 silent-failure mode for benchmark answers."
                    )

    # Limits
    if len(sqlfns) > 50:
        errors.append("instructions.sql_functions exceeds 50-entry limit — truncate before POST")
    if len(bench) > 50:
        errors.append("benchmarks.questions exceeds 50-entry limit — truncate before POST")

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
    print(f"    description: 'Persisted Genie Space id for {r['title']!s} (do NOT edit)'")
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

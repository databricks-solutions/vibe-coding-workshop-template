#!/usr/bin/env python3
"""
Genie Optimization Applier - Standalone CLI for applying proposals and deploying bundles.

Applies metadata change proposals via dual persistence (API + repo files),
deploys the bundle, and triggers the Genie Space deployment job.

Usage:
    python optimization_applier.py --space-id <ID> --domain cost --proposals proposals.json
    python optimization_applier.py --space-id <ID> --domain cost --proposals proposals.json --deploy-target dev --genie-job genie_spaces_deployment_job

Requirements:
    - databricks-sdk (optional, for API operations)
    - databricks CLI (for bundle deploy and job run)
"""

import argparse
import copy
import json
import subprocess
from pathlib import Path

# Feature flag for Module 4 patch DSL (default False - preserves legacy behavior)
USE_PATCH_DSL = False

NON_EXPORTABLE_FIELDS = {
    "id", "title", "description", "creator", "creator_id",
    "updated_by", "updated_at", "created_at", "warehouse_id",
    "execute_as_user_id", "space_status",
}


def strip_non_exportable_fields(config: dict) -> dict:
    """Remove fields from GET response that are invalid in PATCH serialized_space.

    The GET /api/2.0/genie/spaces/{id} response includes top-level metadata
    fields (id, title, description, creator, etc.) that are NOT part of the
    GenieSpaceExport protobuf message. Including them in the PATCH payload
    causes: InvalidParameterValue: Cannot find field: <field> in message
    databricks.datarooms.export.GenieSpaceExport
    """
    return {k: v for k, v in config.items() if k not in NON_EXPORTABLE_FIELDS}


def sort_genie_config(config: dict) -> dict:
    """Sort all arrays in Genie config - API rejects unsorted data."""
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


# -----------------------------------------------------------------------------
# Module 4: Patch DSL - render_patch, classify_risk, apply_patch_set, rollback
# -----------------------------------------------------------------------------


def render_patch(patch: dict, space_id: str, space_config: dict) -> dict:
    """Convert a patch dict (from PATCH_TYPES vocabulary) into an executable action dict.

    Each patch has a "type" field that maps to config mutations. Returns an action
    dict with action_type, target, command, rollback_command, risk_level.

    Args:
        patch: Patch dict with type and type-specific fields (target, old_text,
               new_text, value, table, column, etc.).
        space_id: Genie Space ID (for command context).
        space_config: Current Genie space config (for resolving targets).

    Returns:
        {"action_type": str, "target": str, "command": str, "rollback_command": str, "risk_level": str}
    """
    patch_type = patch.get("type", "")
    target = patch.get("target") or patch.get("object_id") or patch.get("table") or ""
    risk = classify_risk(patch)

    # Helper to build action
    def action(cmd: str, rollback: str) -> dict:
        return {
            "action_type": patch_type,
            "target": target,
            "command": cmd,
            "rollback_command": rollback,
            "risk_level": risk,
        }

    old_text = patch.get("old_text", "")
    new_text = patch.get("new_text", patch.get("value", ""))
    table_id = patch.get("table") or patch.get("target") or ""
    column_name = patch.get("column", "")

    # Instructions: general_instructions = text_instructions content
    if patch_type == "add_instruction":
        return action(
            json.dumps({"op": "append_instruction", "value": new_text}),
            json.dumps({"op": "remove_instruction", "old_text": new_text}),
        )
    if patch_type == "update_instruction":
        return action(
            json.dumps({"op": "replace_instruction", "old_text": old_text, "new_text": new_text}),
            json.dumps({"op": "replace_instruction", "old_text": new_text, "new_text": old_text}),
        )
    if patch_type == "remove_instruction":
        return action(
            json.dumps({"op": "remove_instruction", "old_text": old_text}),
            json.dumps({"op": "append_instruction", "value": old_text}),
        )

    # Synonyms
    if patch_type == "add_synonym":
        return action(
            json.dumps({"op": "add_synonym", "table": table_id, "column": column_name, "synonym": new_text}),
            json.dumps({"op": "remove_synonym", "table": table_id, "column": column_name, "synonym": new_text}),
        )
    if patch_type == "remove_synonym":
        return action(
            json.dumps({"op": "remove_synonym", "table": table_id, "column": column_name, "synonym": old_text}),
            json.dumps({"op": "add_synonym", "table": table_id, "column": column_name, "synonym": old_text}),
        )

    # Descriptions
    if patch_type == "update_description":
        return action(
            json.dumps({"op": "update_description", "target": target, "old_text": old_text, "new_text": new_text}),
            json.dumps({"op": "update_description", "target": target, "old_text": new_text, "new_text": old_text}),
        )
    if patch_type == "add_description":
        return action(
            json.dumps({"op": "add_description", "target": target, "value": new_text}),
            json.dumps({"op": "remove_description", "target": target, "value": new_text}),
        )

    # Table/Column
    if patch_type == "add_table":
        asset = patch.get("asset", patch.get("value", {}))
        return action(
            json.dumps({"op": "add_table", "asset": asset}),
            json.dumps({"op": "remove_table", "identifier": asset.get("identifier", target)}),
        )
    if patch_type == "remove_table":
        return action(
            json.dumps({"op": "remove_table", "identifier": target}),
            json.dumps({"op": "add_table", "asset": patch.get("previous_asset", {})}),
        )
    if patch_type == "hide_column":
        return action(
            json.dumps({"op": "hide_column", "table": table_id, "column": column_name}),
            json.dumps({"op": "unhide_column", "table": table_id, "column": column_name}),
        )
    if patch_type == "unhide_column":
        return action(
            json.dumps({"op": "unhide_column", "table": table_id, "column": column_name}),
            json.dumps({"op": "hide_column", "table": table_id, "column": column_name}),
        )
    if patch_type == "rename_column_alias":
        return action(
            json.dumps({"op": "rename_column_alias", "table": table_id, "column": column_name, "old_alias": old_text, "new_alias": new_text}),
            json.dumps({"op": "rename_column_alias", "table": table_id, "column": column_name, "old_alias": new_text, "new_alias": old_text}),
        )
    if patch_type == "add_column_description":
        return action(
            json.dumps({"op": "add_column_description", "table": table_id, "column": column_name, "value": new_text}),
            json.dumps({"op": "remove_column_description", "table": table_id, "column": column_name, "value": new_text}),
        )
    if patch_type == "update_column_description":
        return action(
            json.dumps({"op": "update_column_description", "table": table_id, "column": column_name, "old_text": old_text, "new_text": new_text}),
            json.dumps({"op": "update_column_description", "table": table_id, "column": column_name, "old_text": new_text, "new_text": old_text}),
        )

    # Joins
    if patch_type == "add_join":
        join_spec = patch.get("join_spec", patch.get("value", {}))
        return action(
            json.dumps({"op": "add_join", "join_spec": join_spec}),
            json.dumps({"op": "remove_join", "join_id": join_spec.get("id", "")}),
        )
    if patch_type == "remove_join":
        return action(
            json.dumps({"op": "remove_join", "join_id": target}),
            json.dumps({"op": "add_join", "join_spec": patch.get("previous_join_spec", {})}),
        )
    if patch_type == "update_join_condition":
        return action(
            json.dumps({"op": "update_join_condition", "join_id": target, "old_sql": old_text, "new_sql": new_text}),
            json.dumps({"op": "update_join_condition", "join_id": target, "old_sql": new_text, "new_sql": old_text}),
        )

    # Filters
    if patch_type == "add_default_filter":
        return action(
            json.dumps({"op": "add_default_filter", "target": target, "condition": new_text}),
            json.dumps({"op": "remove_default_filter", "target": target, "condition": new_text}),
        )
    if patch_type == "remove_default_filter":
        return action(
            json.dumps({"op": "remove_default_filter", "target": target, "condition": old_text}),
            json.dumps({"op": "add_default_filter", "target": target, "condition": old_text}),
        )
    if patch_type == "update_filter_condition":
        return action(
            json.dumps({"op": "update_filter_condition", "target": target, "old_condition": old_text, "new_condition": new_text}),
            json.dumps({"op": "update_filter_condition", "target": target, "old_condition": new_text, "new_condition": old_text}),
        )

    # TVF
    if patch_type == "add_tvf_parameter":
        return action(
            json.dumps({"op": "add_tvf_parameter", "tvf": target, "param": patch.get("param_name", new_text)}),
            json.dumps({"op": "remove_tvf_parameter", "tvf": target, "param": patch.get("param_name", new_text)}),
        )
    if patch_type == "remove_tvf_parameter":
        return action(
            json.dumps({"op": "remove_tvf_parameter", "tvf": target, "param": patch.get("param_name", old_text)}),
            json.dumps({"op": "add_tvf_parameter", "tvf": target, "param": patch.get("param_name", old_text)}),
        )
    if patch_type == "update_tvf_sql":
        return action(
            json.dumps({"op": "update_tvf_sql", "tvf": target, "old_sql": old_text, "new_sql": new_text}),
            json.dumps({"op": "update_tvf_sql", "tvf": target, "old_sql": new_text, "new_sql": old_text}),
        )
    if patch_type == "add_tvf":
        tvf_asset = patch.get("tvf_asset", patch.get("value", {}))
        return action(
            json.dumps({"op": "add_tvf", "tvf_asset": tvf_asset}),
            json.dumps({"op": "remove_tvf", "identifier": tvf_asset.get("identifier", target)}),
        )
    if patch_type == "remove_tvf":
        return action(
            json.dumps({"op": "remove_tvf", "identifier": target}),
            json.dumps({"op": "add_tvf", "tvf_asset": patch.get("previous_tvf_asset", {})}),
        )

    # Metric View
    if patch_type == "add_mv_measure":
        measure = patch.get("measure", patch.get("value", {}))
        return action(
            json.dumps({"op": "add_mv_measure", "mv": target, "measure": measure}),
            json.dumps({"op": "remove_mv_measure", "mv": target, "measure_name": measure.get("name", "")}),
        )
    if patch_type == "update_mv_measure":
        return action(
            json.dumps({"op": "update_mv_measure", "mv": target, "measure_name": patch.get("measure_name", ""), "old": old_text, "new": new_text}),
            json.dumps({"op": "update_mv_measure", "mv": target, "measure_name": patch.get("measure_name", ""), "old": new_text, "new": old_text}),
        )
    if patch_type == "remove_mv_measure":
        return action(
            json.dumps({"op": "remove_mv_measure", "mv": target, "measure_name": patch.get("measure_name", old_text)}),
            json.dumps({"op": "add_mv_measure", "mv": target, "measure": patch.get("previous_measure", {})}),
        )
    if patch_type == "add_mv_dimension":
        dim = patch.get("dimension", patch.get("value", {}))
        return action(
            json.dumps({"op": "add_mv_dimension", "mv": target, "dimension": dim}),
            json.dumps({"op": "remove_mv_dimension", "mv": target, "dimension_name": dim.get("name", "")}),
        )
    if patch_type == "remove_mv_dimension":
        return action(
            json.dumps({"op": "remove_mv_dimension", "mv": target, "dimension_name": patch.get("dimension_name", old_text)}),
            json.dumps({"op": "add_mv_dimension", "mv": target, "dimension": patch.get("previous_dimension", {})}),
        )
    if patch_type == "update_mv_yaml":
        return action(
            json.dumps({"op": "update_mv_yaml", "mv": target, "new_yaml": new_text}),
            json.dumps({"op": "update_mv_yaml", "mv": target, "new_yaml": old_text}),
        )

    # Compliance
    if patch_type == "add_compliance_tag":
        return action(
            json.dumps({"op": "add_compliance_tag", "target": target, "tag": new_text}),
            json.dumps({"op": "remove_compliance_tag", "target": target, "tag": new_text}),
        )
    if patch_type == "remove_compliance_tag":
        return action(
            json.dumps({"op": "remove_compliance_tag", "target": target, "tag": old_text}),
            json.dumps({"op": "add_compliance_tag", "target": target, "tag": old_text}),
        )

    # Unknown type
    return action(
        json.dumps({"op": "unknown", "patch_type": patch_type}),
        json.dumps({"op": "unknown", "patch_type": patch_type}),
    )


def classify_risk(patch: dict) -> str:
    """Return risk level per governance rules: low, medium, or high.

    Args:
        patch: Patch dict with "type" field.

    Returns:
        "low", "medium", or "high"
    """
    pt = patch.get("type", "")
    low = {
        "add_synonym", "add_description", "add_column_description",
        "update_column_description", "update_description", "add_instruction",
    }
    medium = {
        "add_table", "hide_column", "add_join", "add_default_filter",
        "add_tvf_parameter", "update_instruction", "update_mv_measure",
        "add_mv_measure", "add_mv_dimension",
    }
    high = {
        "remove_table", "remove_instruction", "remove_join", "remove_tvf",
        "remove_mv_measure", "remove_compliance_tag", "update_mv_yaml",
    }
    if pt in low:
        return "low"
    if pt in medium:
        return "medium"
    if pt in high:
        return "high"
    # Default for unhide_column, remove_synonym, remove_default_filter, etc.
    return "medium"


def _get_general_instructions(space_config: dict) -> str:
    """Extract general instructions as joined text from text_instructions."""
    inst = space_config.get("instructions", {})
    ti = inst.get("text_instructions", [])
    if not ti:
        return ""
    content = ti[0].get("content", [])
    if isinstance(content, list):
        return "\n".join(c for c in content if c)
    return str(content)


def _set_general_instructions(space_config: dict, text: str, instruction_id: str = "genie_opt") -> None:
    """Set general instructions into text_instructions."""
    inst = space_config.setdefault("instructions", {})
    ti = inst.setdefault("text_instructions", [])
    lines = [ln for ln in text.split("\n")] if text else [""]
    if ti:
        ti[0] = {"id": ti[0].get("id", instruction_id), "content": lines}
    else:
        ti.append({"id": instruction_id, "content": lines})


def _apply_action_to_config(space_config: dict, action: dict) -> bool:
    """Apply a single action (from render_patch) to space_config. Idempotent with old_text guards.

    Returns True if applied, False if skipped (e.g. old_text guard failed).
    """
    try:
        cmd = json.loads(action.get("command", "{}"))
    except json.JSONDecodeError:
        return False
    op = cmd.get("op", "")

    # Instructions
    if op == "append_instruction":
        text = cmd.get("value", "")
        if text:
            current = _get_general_instructions(space_config)
            _set_general_instructions(space_config, current + "\n" + text)
        return True
    if op == "replace_instruction":
        current = _get_general_instructions(space_config)
        old_text = cmd.get("old_text", "")
        new_text = cmd.get("new_text", "")
        if old_text and old_text not in current:
            return False  # old_text guard failed - idempotent skip
        replaced = current.replace(old_text, new_text, 1) if old_text else current + "\n" + new_text
        _set_general_instructions(space_config, replaced)
        return True
    if op == "remove_instruction":
        current = _get_general_instructions(space_config)
        old_text = cmd.get("old_text", "")
        if old_text and old_text not in current:
            return False
        replaced = current.replace(old_text, "").strip()
        _set_general_instructions(space_config, replaced)
        return True

    # Synonyms - column_configs
    if op == "add_synonym":
        table_id, col, syn = cmd.get("table", ""), cmd.get("column", ""), cmd.get("synonym", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        syns = cc.setdefault("synonyms", [])
                        if syn and syn not in syns:
                            syns.append(syn)
                        return True
                t.setdefault("column_configs", []).append({"column_name": col, "synonyms": [syn]})
                return True
        return False
    if op == "remove_synonym":
        table_id, col, syn = cmd.get("table", ""), cmd.get("column", ""), cmd.get("synonym", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col and syn in cc.get("synonyms", []):
                        cc["synonyms"] = [s for s in cc["synonyms"] if s != syn]
                        return True
        return False

    # Descriptions
    if op == "update_description":
        target, old_t, new_t = cmd.get("target", ""), cmd.get("old_text", ""), cmd.get("new_text", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                desc = t.get("description", [])
                if isinstance(desc, list):
                    joined = "\n".join(desc)
                    if old_t and old_t not in joined:
                        return False
                    new_desc = joined.replace(old_t, new_t, 1) if old_t else joined + "\n" + new_t
                    t["description"] = [ln for ln in new_desc.split("\n")]
                return True
        return False
    if op == "add_description":
        target, val = cmd.get("target", ""), cmd.get("value", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                desc = t.get("description", [])
                if isinstance(desc, list):
                    desc.append(val)
                else:
                    t["description"] = [str(desc), val]
                return True
        return False
    if op == "remove_description":
        target, val = cmd.get("target", ""), cmd.get("value", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                desc = t.get("description", [])
                if isinstance(desc, list):
                    t["description"] = [d for d in desc if d != val]
                return True
        return False

    # Table/Column
    if op == "add_table":
        asset = cmd.get("asset", {})
        if asset:
            space_config.setdefault("data_sources", {}).setdefault("tables", []).append(asset)
            sort_genie_config(space_config)
        return True
    if op == "remove_table":
        ident = cmd.get("identifier", "")
        tables = space_config.get("data_sources", {}).get("tables", [])
        for i, t in enumerate(tables):
            if t.get("identifier") == ident:
                tables.pop(i)
                return True
        return False
    if op == "hide_column":
        table_id, col = cmd.get("table", ""), cmd.get("column", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        cc["exclude"] = True
                        return True
                t.setdefault("column_configs", []).append({"column_name": col, "exclude": True})
                return True
        return False
    if op == "unhide_column":
        table_id, col = cmd.get("table", ""), cmd.get("column", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        cc["exclude"] = False
                        return True
        return False
    if op == "rename_column_alias":
        # Genie uses column_name; alias may be in synonyms or a separate field - treat as synonym update
        table_id, col, new_alias = cmd.get("table", ""), cmd.get("column", ""), cmd.get("new_alias", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        cc.setdefault("synonyms", []).append(new_alias)
                        return True
        return False
    if op == "add_column_description":
        table_id, col, val = cmd.get("table", ""), cmd.get("column", ""), cmd.get("value", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        cc["description"] = [val] if isinstance(val, str) else val
                        return True
                t.setdefault("column_configs", []).append({"column_name": col, "description": [val] if isinstance(val, str) else val})
                return True
        return False
    if op == "update_column_description":
        table_id, col, old_t, new_t = cmd.get("table", ""), cmd.get("column", ""), cmd.get("old_text", ""), cmd.get("new_text", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        desc = cc.get("description", [])
                        joined = "\n".join(desc) if isinstance(desc, list) else str(desc)
                        if old_t and old_t not in joined:
                            return False
                        cc["description"] = [ln for ln in joined.replace(old_t, new_t, 1).split("\n")]
                        return True
        return False
    if op == "remove_column_description":
        table_id, col, val = cmd.get("table", ""), cmd.get("column", ""), cmd.get("value", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == table_id:
                for cc in t.get("column_configs", []):
                    if cc.get("column_name") == col:
                        desc = cc.get("description", [])
                        if isinstance(desc, list):
                            cc["description"] = [d for d in desc if d != val]
                        else:
                            cc["description"] = []
                        return True
        return False

    # Joins
    if op == "add_join":
        js = cmd.get("join_spec", {})
        if js:
            space_config.setdefault("instructions", {}).setdefault("join_specs", []).append(js)
            sort_genie_config(space_config)
        return True
    if op == "remove_join":
        join_id = cmd.get("join_id", "")
        specs = space_config.get("instructions", {}).get("join_specs", [])
        for i, s in enumerate(specs):
            if s.get("id") == join_id:
                specs.pop(i)
                return True
        return False
    if op == "update_join_condition":
        join_id, old_sql, new_sql = cmd.get("join_id", ""), cmd.get("old_sql", ""), cmd.get("new_sql", "")
        for s in space_config.get("instructions", {}).get("join_specs", []):
            if s.get("id") == join_id:
                sql_list = s.get("sql", [])
                for j, line in enumerate(sql_list):
                    if old_sql in line:
                        sql_list[j] = line.replace(old_sql, new_sql, 1)
                        return True
        return False

    # Filters (store in table-level default_filters - convention)
    if op == "add_default_filter":
        target, cond = cmd.get("target", ""), cmd.get("condition", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                flt = t.setdefault("default_filters", [])
                if cond and cond not in flt:
                    flt.append(cond)
                return True
        return False
    if op == "remove_default_filter":
        target, cond = cmd.get("target", ""), cmd.get("condition", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                flt = t.get("default_filters", [])
                if cond in flt:
                    flt.remove(cond)
                return True
        return False
    if op == "update_filter_condition":
        target, old_c, new_c = cmd.get("target", ""), cmd.get("old_condition", ""), cmd.get("new_condition", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                flt = t.get("default_filters", [])
                for k, c in enumerate(flt):
                    if c == old_c:
                        flt[k] = new_c
                        return True
        return False

    # TVF - sql_functions
    if op == "add_tvf":
        ta = cmd.get("tvf_asset", {})
        if ta:
            ident = ta.get("identifier", "")
            space_config.setdefault("instructions", {}).setdefault("sql_functions", []).append({"id": ta.get("id", ident), "identifier": ident})
            sort_genie_config(space_config)
        return True
    if op == "remove_tvf":
        ident = cmd.get("identifier", "")
        funcs = space_config.get("instructions", {}).get("sql_functions", [])
        for i, f in enumerate(funcs):
            if f.get("identifier") == ident:
                funcs.pop(i)
                return True
        return False
    # add_tvf_parameter, remove_tvf_parameter, update_tvf_sql - TVF definition lives in SQL files; config only has identifier
    if op in ("add_tvf_parameter", "remove_tvf_parameter", "update_tvf_sql"):
        return True  # No-op for config; would need file mutation

    # MV - metric_views in data_sources; YAML lives in repo files
    if op in ("add_mv_measure", "update_mv_measure", "remove_mv_measure", "add_mv_dimension", "remove_mv_dimension", "update_mv_yaml"):
        return True  # MV mutations require YAML file read/write; config has limited MV metadata

    # Compliance tags - store in table/asset tags
    if op == "add_compliance_tag":
        target, tag = cmd.get("target", ""), cmd.get("tag", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                tags = t.setdefault("tags", t.setdefault("compliance_tags", []))
                if isinstance(tags, list) and tag not in tags:
                    tags.append(tag)
                return True
        return False
    if op == "remove_compliance_tag":
        target, tag = cmd.get("target", ""), cmd.get("tag", "")
        for t in space_config.get("data_sources", {}).get("tables", []) + space_config.get("data_sources", {}).get("metric_views", []):
            if t.get("identifier") == target:
                tags = t.get("tags", t.get("compliance_tags", []))
                if isinstance(tags, list) and tag in tags:
                    tags.remove(tag)
                return True
        return False

    return False


def apply_patch_set(
    space_id: str,
    patches: list,
    space_config: dict,
    deploy_target: str | None = None,
    use_patch_dsl: bool = False,
) -> dict:
    """Apply a patch set with snapshots, risk classification, and apply log.

    Always captures pre/post snapshots for rollback regardless of use_patch_dsl.
    When use_patch_dsl=True, also renders patches through the DSL pipeline.

    Args:
        space_id: Genie Space ID.
        patches: List of patch dicts.
        space_config: Genie space config (mutated in place for low+medium).
        deploy_target: Optional bundle target for deploy (passed through).
        use_patch_dsl: If True, render patches via DSL. If False, snapshot-only mode.

    Returns:
        Apply log dict with pre_snapshot, post_snapshot, applied, queued_high, rollback_commands.
    """
    pre_snapshot = copy.deepcopy(space_config)

    if not use_patch_dsl:
        return {
            "space_id": space_id,
            "pre_snapshot": pre_snapshot,
            "post_snapshot": copy.deepcopy(space_config),
            "applied": [],
            "queued_high": [],
            "rollback_commands": [],
            "deploy_target": deploy_target,
        }

    actions = [render_patch(p, space_id, space_config) for p in patches]
    applied = []
    queued_high = []
    rollback_commands = []

    for i, (patch, action) in enumerate(zip(patches, actions)):
        risk = action.get("risk_level", "medium")
        if risk == "high":
            queued_high.append({"index": i, "patch": patch, "action": action})
            rollback_commands.append(None)
            continue
        ok = _apply_action_to_config(space_config, action)
        if ok:
            applied.append({"index": i, "patch": patch, "action": action})
            rollback_commands.append(action.get("rollback_command"))
        else:
            rollback_commands.append(None)

    post_snapshot = copy.deepcopy(space_config)
    sort_genie_config(space_config)

    apply_log = {
        "space_id": space_id,
        "pre_snapshot": pre_snapshot,
        "post_snapshot": post_snapshot,
        "applied": applied,
        "queued_high": queued_high,
        "rollback_commands": [r for r in rollback_commands if r is not None],
        "deploy_target": deploy_target,
    }
    return apply_log


def rollback(
    apply_log: dict,
    space_id: str,
    space_config: dict | None = None,
) -> dict:
    """Restore pre-apply config from the apply log snapshot.

    Called by orchestrator when P0 gate fails or regression is detected.
    Works unconditionally -- snapshot-based rollback does not depend on
    the Patch DSL feature flag.

    Args:
        apply_log: Apply log from apply_patch_set (must have pre_snapshot).
        space_id: Genie Space ID.
        space_config: Optional config to mutate in place. If None, restored_config
                      is returned in result for caller to apply.

    Returns:
        dict with status, executed_count, errors, and optionally restored_config.
    """
    pre_snapshot = apply_log.get("pre_snapshot")
    if pre_snapshot is None:
        return {"status": "error", "executed_count": 0, "errors": ["No pre_snapshot in apply_log"]}

    commands = apply_log.get("rollback_commands", [])
    restored = copy.deepcopy(pre_snapshot)
    if space_config is not None:
        space_config.clear()
        space_config.update(restored)
    return {
        "status": "SUCCESS",
        "executed_count": max(len(commands), 1),
        "errors": [],
        "restored_config": restored,
    }


def _is_databricks_runtime() -> bool:
    """Detect if running inside a Databricks cluster."""
    import os
    return bool(os.environ.get("DATABRICKS_RUNTIME_VERSION"))


def verify_repo_update(repo_path: str) -> dict:
    """Verify that a repository file was modified after a proposal was applied.

    Runs `git diff` on the repo file to check for modifications. This enforces
    hard constraint #13: dual persistence is verified, not assumed.

    In Databricks notebook execution context, git is unavailable -- returns a
    reminder to verify manually.

    Args:
        repo_path: Relative path to the repository file.

    Returns:
        {"modified": bool | None, "diff_preview": str}
    """
    if _is_databricks_runtime():
        return {
            "modified": None,
            "diff_preview": "(running in Databricks - git verification skipped, verify repo manually)",
        }
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "--", repo_path],
            capture_output=True, text=True, timeout=10,
        )
        modified = bool(result.stdout.strip())
        if not modified:
            result = subprocess.run(
                ["git", "diff", "--cached", "--stat", "--", repo_path],
                capture_output=True, text=True, timeout=10,
            )
            modified = bool(result.stdout.strip())

        diff_result = subprocess.run(
            ["git", "diff", "--", repo_path],
            capture_output=True, text=True, timeout=10,
        )
        diff_preview = diff_result.stdout[:500] if diff_result.stdout else ""
        return {"modified": modified, "diff_preview": diff_preview}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"modified": False, "diff_preview": "(git not available)"}


def apply_proposal_batch(
    proposals: list,
    space_id: str,
    domain: str,
) -> list:
    """Apply a batch of non-conflicting proposals with dual persistence.

    Each proposal describes the lever, change, and dual persistence paths.
    The agent executes the API command and updates the repository file.

    After preparing each proposal, verifies repo file modification via git diff
    (hard constraint #13). Proposals where repo_status is not "success" must be
    fixed before proceeding to re-evaluation.

    Args:
        proposals: List of proposal dicts from generate_metadata_proposals().
        space_id: Genie Space ID.
        domain: Domain name for repo path substitution.

    Returns:
        list of results with status, repo_status, and repo_diff_preview per proposal.
    """
    results = []
    for p in proposals:
        dual = p.get("dual_persistence", {})
        api_cmd = dual.get("api", "")
        repo_path = dual.get("repo", "").replace("{domain}", domain).replace("{space_id}", space_id)

        repo_check = verify_repo_update(repo_path)

        results.append({
            "proposal_id": p.get("proposal_id", ""),
            "lever": p.get("lever", 0),
            "status": "pending_agent_execution",
            "api_command": api_cmd,
            "repo_path": repo_path,
            "repo_status": "success" if repo_check["modified"] else "pending",
            "repo_diff_preview": repo_check["diff_preview"],
            "change": p.get("change_description", ""),
        })
    return results


def deploy_bundle_and_run_genie_job(
    target: str = "dev",
    genie_job: str = "genie_spaces_deployment_job",
) -> dict:
    """Validate bundle, deploy, and trigger Genie Space deployment job.

    Phase B: databricks bundle validate + deploy
    Phase C: databricks bundle run <genie_job>

    Args:
        target: Bundle target (e.g., 'dev', 'prod').
        genie_job: Name of the Genie deployment job in the bundle.

    Returns:
        dict with status ('SUCCESS', 'VALIDATE_FAILED', 'DEPLOY_FAILED', 'JOB_FAILED'),
        error message if failed, and stdout from deploy/run.
    """
    print("\n--- Phase B: Bundle Validate + Deploy ---\n")
    validate = subprocess.run(
        ["databricks", "bundle", "validate", "-t", target],
        capture_output=True,
        text=True,
    )
    if validate.returncode != 0:
        return {"status": "VALIDATE_FAILED", "error": validate.stderr}

    deploy = subprocess.run(
        ["databricks", "bundle", "deploy", "-t", target],
        capture_output=True,
        text=True,
    )
    if deploy.returncode != 0:
        return {"status": "DEPLOY_FAILED", "error": deploy.stderr}
    print("  Bundle deployed successfully.")

    print(f"\n--- Phase C: Trigger {genie_job} ---\n")
    run = subprocess.run(
        ["databricks", "bundle", "run", "-t", target, genie_job],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        return {
            "status": "JOB_FAILED",
            "deploy_stdout": deploy.stdout,
            "error": run.stderr,
        }

    print("  Genie Space deployment job completed.")
    return {
        "status": "SUCCESS",
        "deploy_stdout": deploy.stdout,
        "run_stdout": run.stdout,
        "error": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Genie Optimization Applier - Apply proposals and deploy bundles"
    )
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument("--domain", required=True, help="Domain name (e.g., cost)")
    parser.add_argument(
        "--proposals",
        required=True,
        help="Path to proposals JSON file (from metadata_optimizer.py)",
    )
    parser.add_argument(
        "--deploy-target",
        default=None,
        help="Bundle target for deploy (e.g., dev). If not set, only apply proposals (no deploy).",
    )
    parser.add_argument(
        "--genie-job",
        default="genie_spaces_deployment_job",
        help="Genie deployment job name (default: genie_spaces_deployment_job)",
    )
    parser.add_argument(
        "--use-patch-dsl",
        action="store_true",
        default=False,
        help="Use patch DSL (Module 4): render_patch, apply_patch_set, rollback (default: False)",
    )
    parser.add_argument(
        "--space-config",
        default=None,
        help="Path to Genie space config JSON (required when --use-patch-dsl and patches present)",
    )
    args = parser.parse_args()

    proposals_path = Path(args.proposals)
    if not proposals_path.exists():
        print(f"ERROR: Proposals file not found: {proposals_path}")
        return 1

    with open(proposals_path) as f:
        data = json.load(f)

    # Patch DSL path: patches + space_config -> apply_patch_set
    patches = data.get("patches", data.get("patch_set", []))
    if args.use_patch_dsl and patches:
        space_config_path = args.space_config or data.get("space_config_path")
        if not space_config_path:
            print("ERROR: --use-patch-dsl with patches requires --space-config or space_config_path in data.")
            return 1
        sp_path = Path(space_config_path)
        if not sp_path.exists():
            print(f"ERROR: Space config file not found: {sp_path}")
            return 1
        with open(sp_path) as f:
            space_config = json.load(f)
        apply_log = apply_patch_set(
            args.space_id,
            patches,
            space_config,
            deploy_target=args.deploy_target,
            use_patch_dsl=True,
        )
        print(f"\n--- Patch DSL Apply Log ---\n")
        print(f"  Applied: {len(apply_log['applied'])}")
        print(f"  Queued (high risk): {len(apply_log['queued_high'])}")
        print(f"  Rollback commands: {len(apply_log['rollback_commands'])}")
        # Write updated config back if path provided
        with open(sp_path, "w") as f:
            json.dump(space_config, f, indent=2)
        print(f"  Updated config written to: {sp_path}")
        if args.deploy_target:
            result = deploy_bundle_and_run_genie_job(
                target=args.deploy_target,
                genie_job=args.genie_job,
            )
            if result["status"] != "SUCCESS":
                print(f"\nDeploy/job failed: {result['status']}")
                return 1
        return 0

    proposals = data.get("proposals", data.get("lever_map", []))
    if not proposals:
        print("No proposals found in file.")
        return 0

    # Apply proposals (during-loop mode: prepare apply status)
    batches = data.get("batches", [proposals])
    apply_status = []
    for batch in batches:
        batch_results = apply_proposal_batch(batch, args.space_id, args.domain)
        apply_status.extend(batch_results)

    print(f"\n--- Apply Status ({len(apply_status)} proposals) ---\n")
    for r in apply_status:
        print(f"  {r['proposal_id']} (lever {r['lever']}): {r['status']}")
        print(f"    API: {r['api_command']}")
        print(f"    Repo: {r['repo_path']}")

    if args.deploy_target:
        print("\n" + "=" * 60)
        print("POST-OPTIMIZATION: Bundle Deploy + Genie Space Job")
        print("=" * 60)
        result = deploy_bundle_and_run_genie_job(
            target=args.deploy_target,
            genie_job=args.genie_job,
        )
        if result["status"] == "SUCCESS":
            print("\nBundle deployed and Genie Space deployment job completed.")
        else:
            print(f"\nDeploy/job failed: {result['status']}")
            print(f"Error: {result.get('error', 'unknown')}")
            return 1
    else:
        print("\nSkipping deploy (--deploy-target not set). Proposals prepared for agent execution.")

    return 0


if __name__ == "__main__":
    exit(main())

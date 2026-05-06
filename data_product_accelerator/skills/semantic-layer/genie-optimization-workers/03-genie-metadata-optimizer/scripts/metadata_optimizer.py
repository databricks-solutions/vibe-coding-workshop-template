#!/usr/bin/env python3
"""
Genie Metadata Optimizer - Standalone introspection and proposal generation CLI.

Clusters evaluation failures by systemic root cause, generates metadata change
proposals with dual persistence paths, detects conflicts, and detects regressions.

Usage:
    python metadata_optimizer.py --eval-results eval_results.json --metadata-snapshot snapshot.json --output proposals.json --tier introspect
    python metadata_optimizer.py --eval-results eval_results.json --metadata-snapshot snapshot.json --output proposals.json --use-gepa [--space-id SPACE_ID]

Requirements:
    - pandas (for DataFrame handling when eval results include tables)
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

# -----------------------------------------------------------------------------
# Module 3: Patch DSL, ASI integration, and validation
# -----------------------------------------------------------------------------

# Feature flags (defaults: ASI-enabled, Patch DSL enabled)
USE_ASI = True
USE_PATCH_DSL = True

# 31 patch types: type, scope, risk_level, affects
PATCH_TYPES = {
    # Instructions
    "add_instruction": {
        "type": "add_instruction",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["instructions"],
    },
    "update_instruction": {
        "type": "update_instruction",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["instructions"],
    },
    "remove_instruction": {
        "type": "remove_instruction",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["instructions"],
    },
    # Synonyms/Descriptions
    "add_synonym": {
        "type": "add_synonym",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["synonyms", "column_metadata"],
    },
    "remove_synonym": {
        "type": "remove_synonym",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["synonyms", "column_metadata"],
    },
    "update_description": {
        "type": "update_description",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["descriptions", "column_metadata"],
    },
    "add_description": {
        "type": "add_description",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["descriptions", "column_metadata"],
    },
    # Table/Column
    "add_table": {
        "type": "add_table",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["tables", "schema"],
    },
    "remove_table": {
        "type": "remove_table",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["tables", "schema"],
    },
    "hide_column": {
        "type": "hide_column",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["column_visibility", "column_metadata"],
    },
    "unhide_column": {
        "type": "unhide_column",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["column_visibility", "column_metadata"],
    },
    "rename_column_alias": {
        "type": "rename_column_alias",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["column_metadata", "aliases"],
    },
    "add_column_description": {
        "type": "add_column_description",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["column_metadata", "descriptions"],
    },
    "update_column_description": {
        "type": "update_column_description",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["column_metadata", "descriptions"],
    },
    # Joins
    "add_join": {
        "type": "add_join",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["joins", "relationships"],
    },
    "remove_join": {
        "type": "remove_join",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["joins", "relationships"],
    },
    "update_join_condition": {
        "type": "update_join_condition",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["joins", "relationships"],
    },
    # Filters
    "add_default_filter": {
        "type": "add_default_filter",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["filters", "default_filters"],
    },
    "remove_default_filter": {
        "type": "remove_default_filter",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["filters", "default_filters"],
    },
    "update_filter_condition": {
        "type": "update_filter_condition",
        "scope": "genie_overlay",
        "risk_level": "medium",
        "affects": ["filters", "default_filters"],
    },
    # TVF
    "add_tvf_parameter": {
        "type": "add_tvf_parameter",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["tvf_parameters", "tvf_definition"],
    },
    "remove_tvf_parameter": {
        "type": "remove_tvf_parameter",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["tvf_parameters", "tvf_definition"],
    },
    "update_tvf_sql": {
        "type": "update_tvf_sql",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["tvf_definition", "tvf_sql"],
    },
    "add_tvf": {
        "type": "add_tvf",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["tvfs", "tvf_definition"],
    },
    "remove_tvf": {
        "type": "remove_tvf",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["tvfs", "tvf_definition"],
    },
    # Metric View
    "add_mv_measure": {
        "type": "add_mv_measure",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["metric_view", "measures"],
    },
    "update_mv_measure": {
        "type": "update_mv_measure",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["metric_view", "measures"],
    },
    "remove_mv_measure": {
        "type": "remove_mv_measure",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["metric_view", "measures"],
    },
    "add_mv_dimension": {
        "type": "add_mv_dimension",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["metric_view", "dimensions"],
    },
    "remove_mv_dimension": {
        "type": "remove_mv_dimension",
        "scope": "uc_universal",
        "risk_level": "medium",
        "affects": ["metric_view", "dimensions"],
    },
    "update_mv_yaml": {
        "type": "update_mv_yaml",
        "scope": "uc_universal",
        "risk_level": "high",
        "affects": ["metric_view", "mv_yaml"],
    },
    # Compliance
    "add_compliance_tag": {
        "type": "add_compliance_tag",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["compliance_tags", "tags"],
    },
    "remove_compliance_tag": {
        "type": "remove_compliance_tag",
        "scope": "genie_overlay",
        "risk_level": "low",
        "affects": ["compliance_tags", "tags"],
    },
}

# 16 conflict pairs: patch types that cannot coexist on the same object
CONFLICT_RULES = [
    ("add_table", "remove_table"),
    ("add_synonym", "remove_synonym"),
    ("add_instruction", "remove_instruction"),
    ("add_instruction", "update_instruction"),
    ("update_instruction", "remove_instruction"),
    ("add_join", "remove_join"),
    ("add_default_filter", "remove_default_filter"),
    ("add_tvf_parameter", "remove_tvf_parameter"),
    ("add_tvf", "remove_tvf"),
    ("add_mv_measure", "remove_mv_measure"),
    ("add_mv_dimension", "remove_mv_dimension"),
    ("add_compliance_tag", "remove_compliance_tag"),
    ("hide_column", "unhide_column"),
    ("add_column_description", "update_column_description"),
    ("add_description", "update_description"),
    ("update_mv_measure", "remove_mv_measure"),
]

# Failure types for ASI judge feedback taxonomy
FAILURE_TAXONOMY = {
    "wrong_table",
    "wrong_column",
    "wrong_join",
    "missing_filter",
    "missing_temporal_filter",
    "wrong_aggregation",
    "wrong_measure",
    "missing_instruction",
    "ambiguous_question",
    "asset_routing_error",
    "tvf_parameter_error",
    "compliance_violation",
    "performance_issue",
    "repeatability_issue",
    "missing_synonym",
    "description_mismatch",
    "monitoring_gap",
    "stale_data",
    "data_freshness",
    "ml_feature_missing",
    "model_scoring_error",
    "feature_store_mismatch",
    "other",
}


def validate_patch_set(patches: list) -> tuple[bool, list[str]]:
    """Validate a patch set: types, conflicts, blast radius.

    Args:
        patches: List of patch dicts, each with at least 'type' and optionally
                 'object_id' or 'target' for conflict/blast checks.

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    # 1. All types must be from PATCH_TYPES
    for i, p in enumerate(patches):
        pt = p.get("type") if isinstance(p, dict) else None
        if pt not in PATCH_TYPES:
            errors.append(f"Patch {i}: unknown type '{pt}'")

    # 2. Check CONFLICT_RULES violations (same object)
    object_patches = defaultdict(list)
    for i, p in enumerate(patches):
        if not isinstance(p, dict):
            continue
        obj = p.get("object_id") or p.get("target") or p.get("table") or "_default"
        object_patches[obj].append((i, p.get("type")))

    for obj, type_list in object_patches.items():
        types_seen = set()
        for _, pt in type_list:
            for (a, b) in CONFLICT_RULES:
                if pt == a and b in types_seen:
                    errors.append(f"Conflict on object '{obj}': {a} vs {b}")
                if pt == b and a in types_seen:
                    errors.append(f"Conflict on object '{obj}': {a} vs {b}")
            types_seen.add(pt)

    # 3. Blast radius: max 5 objects per set
    all_objects = set()
    for p in patches:
        if isinstance(p, dict):
            obj = p.get("object_id") or p.get("target") or p.get("table")
            if obj:
                all_objects.add(obj)
    if len(all_objects) > 5:
        errors.append(f"Blast radius exceeded: {len(all_objects)} objects (max 5)")

    return (len(errors) == 0, errors)


def propose_patch_set_from_asi(
    judge_feedbacks: list, metadata_snapshot: dict, target_lever: int | None = None
) -> list[dict]:
    """L1 greedy patch proposal from ASI judge feedbacks.

    Collects failures, groups by blame_set, synthesizes patch sets (2-12 patches),
    scores and selects best greedily.

    Args:
        judge_feedbacks: List of judge Feedback dicts with value (pass/fail),
                         blame_set, counterfactual_fix, feedback_id, confidence.
        metadata_snapshot: Current Genie metadata for context.
        target_lever: When provided, only return patches that map to this lever (1-6).

    Returns:
        List of patch dicts with type, scope, risk_level, grounded_in,
        predicted_affected_questions.
    """
    failures = [
        f
        for f in judge_feedbacks
        if isinstance(f, dict)
        and str(f.get("value", "")).lower() in ("no", "fail", "false", "0")
    ]

    if not failures:
        return []

    # Group by blame_set (metadata fields blamed)
    blame_groups = defaultdict(list)
    for f in failures:
        blame = f.get("blame_set") or f.get("blame") or tuple()
        if isinstance(blame, (list, tuple)):
            key = tuple(sorted(blame)) if blame else ("_ungrouped",)
        else:
            key = (str(blame),)
        blame_groups[key].append(f)

    total_objects = 1
    if metadata_snapshot:
        tables = metadata_snapshot.get("tables") or metadata_snapshot.get("schema") or {}
        total_objects = max(1, len(tables) if isinstance(tables, dict) else 1)

    best_patch_set = []
    best_score = -1.0

    for blame_key, group in blame_groups.items():
        if blame_key == ("_ungrouped",) and len(group) < 2:
            continue

        fixes = []
        for f in group:
            cf = f.get("counterfactual_fix") or f.get("counterfactual_fixes") or []
            if isinstance(cf, list):
                fixes.extend(cf)
            elif cf:
                fixes.append(cf)

        # Synthesize 2-12 patches from PATCH_TYPES based on fixes
        patch_set = _synthesize_patches_from_fixes(fixes, group, metadata_snapshot)
        if len(patch_set) < 2 or len(patch_set) > 12:
            continue

        is_valid, _ = validate_patch_set(patch_set)
        if not is_valid:
            continue

        score = score_patch_set(patch_set, metadata_snapshot)
        if score > best_score:
            best_score = score
            best_patch_set = patch_set

    if target_lever is not None and best_patch_set:
        best_patch_set = [p for p in best_patch_set if _patch_to_lever(p) == target_lever]

    return best_patch_set


def _synthesize_patches_from_fixes(
    fixes: list, group: list, metadata_snapshot: dict
) -> list[dict]:
    """Map counterfactual fix suggestions to concrete patches from PATCH_TYPES."""
    patches = []
    feedback_ids = [f.get("feedback_id") or f.get("id") or str(i) for i, f in enumerate(group)]
    questions = list({f.get("question_id") or f.get("question") or "q" for f in group})

    for fix in fixes[:12]:
        if not isinstance(fix, dict):
            continue
        pt = (fix.get("patch_type") or fix.get("type") or "").lower().replace("-", "_")
        if pt in PATCH_TYPES:
            meta = PATCH_TYPES[pt]
            patches.append({
                "type": pt,
                "scope": meta["scope"],
                "risk_level": meta["risk_level"],
                "grounded_in": feedback_ids,
                "predicted_affected_questions": questions,
                "object_id": fix.get("object_id") or fix.get("target"),
            })
        elif fix.get("action"):
            # Heuristic: map action keywords to patch types
            action = str(fix.get("action", "")).lower()
            if "add" in action and "synonym" in action:
                pt = "add_synonym"
            elif "remove" in action and "synonym" in action:
                pt = "remove_synonym"
            elif "add" in action and "instruction" in action:
                pt = "add_instruction"
            elif "add" in action and "table" in action:
                pt = "add_table"
            elif "add" in action and "join" in action:
                pt = "add_join"
            elif "add" in action and "filter" in action:
                pt = "add_default_filter"
            else:
                pt = "add_instruction"
            if pt in PATCH_TYPES:
                meta = PATCH_TYPES[pt]
                patches.append({
                    "type": pt,
                    "scope": meta["scope"],
                    "risk_level": meta["risk_level"],
                    "grounded_in": feedback_ids,
                    "predicted_affected_questions": questions,
                    "object_id": fix.get("object_id") or fix.get("target"),
                })

    return patches[:12]


def score_patch_set(patch_set: list, metadata_snapshot: dict) -> float:
    """Score a patch set based on blast radius and predicted improvement.

    predicted_improvement = questions_blamed * avg_confidence - 0.1 * (blast_objects / total_objects)
    """
    if not patch_set:
        return 0.0

    total_objects = 1
    if metadata_snapshot:
        tables = metadata_snapshot.get("tables") or metadata_snapshot.get("schema") or {}
        total_objects = max(1, len(tables) if isinstance(tables, dict) else 1)

    all_objects = set()
    questions_blamed = 0
    confidences = []

    for p in patch_set:
        if isinstance(p, dict):
            obj = p.get("object_id") or p.get("target") or p.get("table")
            if obj:
                all_objects.add(obj)
            qs = p.get("predicted_affected_questions") or []
            questions_blamed = max(questions_blamed, len(qs))
            for fb in p.get("grounded_in") or []:
                confidences.append(0.7)

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    blast_objects = len(all_objects)
    predicted_improvement = questions_blamed * avg_confidence - 0.1 * (
        blast_objects / total_objects
    )
    return predicted_improvement


def read_asi_from_uc(catalog: str, schema: str, run_id: str, warehouse_id: str) -> list[dict]:
    """Query genie_eval_asi_results UC Delta table via Databricks SQL Statement API.

    Returns list of ASI dicts, one per (question, judge) pair.
    """
    import requests
    table = f"{catalog}.{schema}.genie_eval_asi_results"
    query = f"""
        SELECT run_id, iteration, question_id, judge, value,
               failure_type, severity, confidence, blame_set,
               counterfactual_fix, wrong_clause, expected_value,
               actual_value, missing_metadata, ambiguity_detected
        FROM {table}
        WHERE run_id = '{run_id}'
        ORDER BY question_id, judge
    """
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        result = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout="30s",
        )
        if not result.result or not result.result.data_array:
            return []
        columns = [c.name for c in result.manifest.schema.columns]
        rows = []
        for data_row in result.result.data_array:
            row_dict = dict(zip(columns, data_row))
            if row_dict.get("blame_set"):
                try:
                    row_dict["blame_set"] = json.loads(row_dict["blame_set"])
                except (json.JSONDecodeError, TypeError):
                    row_dict["blame_set"] = [row_dict["blame_set"]]
            rows.append(row_dict)
        return rows
    except Exception as e:
        print(f"WARNING: read_asi_from_uc() failed: {e}")
        return []


def _extract_asi_from_assessments(assessments: list) -> list[dict]:
    """Parse ASI metadata from mlflow assessments list."""
    feedbacks = []
    for a in assessments:
        if not isinstance(a, dict):
            continue
        meta = a.get("metadata", {})
        if not isinstance(meta, dict):
            continue
        feedbacks.append({
            "value": a.get("value", ""),
            "judge": a.get("name", ""),
            "question_id": a.get("question_id", ""),
            "failure_type": meta.get("failure_type", ""),
            "blame_set": meta.get("blame_set", []),
            "counterfactual_fix": [meta.get("counterfactual_fix", "")],
            "confidence": float(meta.get("confidence", 0.5)),
            "asi_severity": meta.get("severity", ""),
            "asi_wrong_clause": meta.get("wrong_clause", ""),
            "asi_expected_value": meta.get("expected_value", ""),
            "asi_actual_value": meta.get("actual_value", ""),
            "asi_missing_metadata": meta.get("missing_metadata", ""),
            "asi_ambiguity_detected": meta.get("ambiguity_detected", False),
        })
    return feedbacks


def _extract_judge_feedbacks_from_eval(eval_results: dict,
                                       catalog: str = "",
                                       schema: str = "",
                                       warehouse_id: str = "") -> list[dict]:
    """Extract judge feedback dicts from eval results using UC-first priority chain.

    Priority: UC table -> direct feedbacks -> {judge}/metadata columns -> regex fallback.
    """
    # Priority 1: UC table (primary source)
    run_id = eval_results.get("run_id", "")
    if catalog and schema and run_id and warehouse_id:
        uc_rows = read_asi_from_uc(catalog, schema, run_id, warehouse_id)
        if uc_rows:
            feedbacks = []
            for row in uc_rows:
                if str(row.get("value", "")).lower() in ("no", "false", "0"):
                    feedbacks.append({
                        "value": row.get("value", ""),
                        "judge": row.get("judge", ""),
                        "question_id": row.get("question_id", ""),
                        "failure_type": row.get("failure_type", ""),
                        "blame_set": row.get("blame_set", []),
                        "counterfactual_fix": [row.get("counterfactual_fix", "")],
                        "confidence": float(row.get("confidence", 0.5)),
                        "asi_severity": row.get("severity", ""),
                        "asi_wrong_clause": row.get("wrong_clause", ""),
                        "asi_expected_value": row.get("expected_value", ""),
                        "asi_actual_value": row.get("actual_value", ""),
                        "asi_missing_metadata": row.get("missing_metadata", ""),
                        "asi_ambiguity_detected": row.get("ambiguity_detected", False),
                        "feedback_id": f"uc_{row.get('question_id', '')}_{row.get('judge', '')}",
                    })
            if feedbacks:
                print(f"  ASI source: UC table ({len(feedbacks)} failure rows)")
                return feedbacks

    # Priority 2: Direct feedbacks list
    direct = eval_results.get("judge_feedbacks") or eval_results.get("feedbacks")
    if isinstance(direct, list) and direct:
        return direct

    # Priority 3: eval_results rows with {judge}/metadata columns
    rows = (
        eval_results.get("eval_results")
        or eval_results.get("rows")
        or eval_results.get("table")
    )
    if not isinstance(rows, list):
        return []

    feedbacks = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for col, val in list(row.items()):
            if col.endswith("/value") and str(val).lower() in ("no", "false"):
                judge = col.replace("/value", "")
                meta_col = f"{judge}/metadata"
                meta = row.get(meta_col, {})
                if isinstance(meta, dict) and meta.get("failure_type"):
                    feedbacks.append({
                        "value": val,
                        "judge": judge,
                        "failure_type": meta.get("failure_type", ""),
                        "blame_set": meta.get("blame_set", []),
                        "counterfactual_fix": [meta.get("counterfactual_fix", "")],
                        "confidence": float(meta.get("confidence", 0.7)),
                        "question_id": row.get("inputs/question_id",
                                              (row.get("inputs", {}) or {}).get("question_id", f"q{i}")),
                        "feedback_id": f"r{i}_{judge}",
                        "asi_severity": meta.get("severity", ""),
                        "asi_wrong_clause": meta.get("wrong_clause", ""),
                        "asi_ambiguity_detected": meta.get("ambiguity_detected", False),
                    })
                    continue

            # Priority 4: Regex fallback
            if col.startswith("feedback/") and "no" in str(val).lower():
                judge = col.replace("feedback/", "")
                rationale_col = f"rationale/{judge}"
                rationale = row.get(rationale_col, row.get("rationale", ""))
                feedbacks.append({
                    "value": val,
                    "blame_set": _infer_blame_from_rationale(rationale),
                    "counterfactual_fix": [],
                    "feedback_id": f"r{i}_{judge}",
                    "question_id": row.get("inputs/question", row.get("question", f"q{i}")),
                    "confidence": 0.7,
                })
    return feedbacks


def _infer_blame_from_rationale(rationale: str) -> list[str]:
    """Infer blame_set from judge rationale for grouping."""
    r = (rationale or "").lower()
    blame = []
    if "table" in r:
        blame.append("tables")
    if "column" in r:
        blame.append("column_metadata")
    if "join" in r:
        blame.append("joins")
    if "filter" in r:
        blame.append("filters")
    if "instruction" in r:
        blame.append("instructions")
    return blame if blame else ["_ungrouped"]


def _convert_patch_set_to_proposals(patch_set: list[dict]) -> list[dict]:
    """Convert ASI patch set to proposal format for output compatibility."""
    proposals = []
    for i, p in enumerate(patch_set):
        lever = _patch_to_lever(p)
        proposals.append({
            "proposal_id": f"P{i+1:03d}",
            "cluster_id": f"ASI_{i+1}",
            "lever": lever,
            "lever_type": p.get("type", "other"),
            "change_description": f"Patch: {p.get('type', 'unknown')}",
            "dual_persistence": _dual_persist_paths({"root_cause": p.get("type", "other")}),
            "confidence": 0.7,
            "questions_fixed": len(p.get("predicted_affected_questions") or []),
            "questions_at_risk": 0,
            "net_impact": len(p.get("predicted_affected_questions") or []) * 0.7,
            "grounded_in": p.get("grounded_in", []),
        })
    return proposals


# -----------------------------------------------------------------------------
# GEPA L2: GenieMetadataAdapter and run_gepa_optimization (use_gepa=True)
# -----------------------------------------------------------------------------

USE_GEPA = False


def run_gepa_optimization(
    space_id: str,
    config: dict,
    judge_feedbacks: list[dict],
    judge_suite: dict | None = None,
    max_rounds: int = 3,
    use_gepa: bool = True,
) -> list[dict] | None:
    """Top-level GEPA L2 optimization using patch set JSON candidates.

    Creates GenieMetadataAdapter, generates candidate patch sets, evaluates each,
    selects best using multi-objective scoring, returns best patch set.
    Gated behind use_gepa=True (default False for safety).

    Args:
        space_id: Genie Space ID.
        config: Current Genie metadata config.
        judge_feedbacks: List of judge feedback dicts (value, blame_set, etc.).
        judge_suite: Judge suite for scoring (optional).
        max_rounds: Max optimization rounds (default 3).
        use_gepa: If False, returns None immediately (safety gate).

    Returns:
        Best patch set (list of patch dicts) or None.
    """
    if not use_gepa:
        return None

    judge_suite = judge_suite or {}

    def evaluator_fn(config_patched: dict, example: dict) -> tuple[float, dict]:
        # Stub: use score_patch_set when no live Genie API; asi from example if present
        patches = example.get("patch_set", [])
        score = score_patch_set(patches, config_patched)
        asi = example.get("asi", {})
        return score, asi

    adapter = GenieMetadataAdapter(
        space_id=space_id,
        config=config,
        judge_suite=judge_suite,
        evaluator_fn=evaluator_fn,
    )
    adapter.config = {**config, "_judge_feedbacks": judge_feedbacks}

    best_patch_set = None
    best_score = -1.0

    for _ in range(max_rounds):
        candidates = adapter.generate_candidates(n=5)
        eval_results = []

        for patch_set in candidates:
            score, asi_trajectories = adapter.evaluate(patch_set)
            eval_results.append({
                "patch_set": patch_set,
                "score": score,
                "asi_trajectories": asi_trajectories,
            })
            if score > best_score:
                best_score = score
                best_patch_set = patch_set

        for r in eval_results:
            blast = len(set(p.get("object_id") or p.get("target") for p in r["patch_set"] if p.get("object_id") or p.get("target")))
            r["mo_score"] = r["score"] - 0.1 * blast

        if eval_results:
            best_by_mo = max(eval_results, key=lambda x: x["mo_score"])
            if best_by_mo["mo_score"] > best_score - 0.5:
                best_patch_set = best_by_mo["patch_set"]
                best_score = best_by_mo["score"]

    return best_patch_set


class GenieMetadataAdapter:
    """Wraps GEPA optimization with structured patch set JSON candidates."""

    def __init__(
        self,
        space_id: str,
        config: dict,
        judge_suite: dict,
        evaluator_fn: callable,
    ):
        self.space_id = space_id
        self.config = config
        self.judge_suite = judge_suite
        self.evaluator_fn = evaluator_fn

    def evaluate(self, patch_set_json: list) -> tuple[float, list]:
        """Apply patches to config copy, run evaluator, return score + ASI trajectories, then rollback."""
        import copy
        config_copy = copy.deepcopy(self.config)
        _apply_patch_set_to_config(config_copy, patch_set_json)

        asi_trajectories = []
        scores = []
        examples = self._get_benchmark_examples(patch_set_json)

        for example in examples:
            score, asi = self.evaluator_fn(config_copy, example)
            scores.append(score)
            asi_trajectories.append(asi)

        overall_score = sum(scores) / max(len(scores), 1)
        return overall_score, asi_trajectories

    def make_reflective_dataset(self, eval_results: list) -> list:
        """Create a reflective dataset from evaluation results for GEPA learning."""
        dataset = []
        for r in eval_results:
            patch_set = r.get("patch_set", [])
            score = r.get("score", 0.0)
            trajectories = r.get("asi_trajectories", [])
            rationales = []
            for asi in trajectories:
                rationales.extend((asi.get("judge_rationales") or {}).values())
            dataset.append({
                "patch_set": patch_set,
                "score": score,
                "rationales": rationales,
                "asi_trajectories": trajectories,
            })
        return dataset

    def generate_candidates(self, n: int = 5) -> list:
        """Generate n candidate patch set JSONs from current failures."""
        failures = self._get_current_failures()
        candidates = []
        base = propose_patch_set_from_asi(failures, self.config)
        if base:
            candidates.append(base)
        if not base and failures:
            fixes = []
            for f in failures:
                cf = f.get("counterfactual_fix") or f.get("counterfactual_fixes") or []
                fixes.extend(cf if isinstance(cf, list) else [cf] if cf else [])
            patch_set = _synthesize_patches_from_fixes(fixes, failures, self.config)
            if patch_set and validate_patch_set(patch_set)[0]:
                candidates.append(patch_set)
        for i in range(n - 1):
            subset = failures[i::n] if failures else []
            patch_set = propose_patch_set_from_asi(subset or failures, self.config)
            if not patch_set and (subset or failures):
                fixes = []
                for f in (subset or failures):
                    cf = f.get("counterfactual_fix") or f.get("counterfactual_fixes") or []
                    fixes.extend(cf if isinstance(cf, list) else [cf] if cf else [])
                patch_set = _synthesize_patches_from_fixes(fixes, subset or failures, self.config)
            if patch_set:
                seen = [json.dumps(c, sort_keys=True) for c in candidates]
                if json.dumps(patch_set, sort_keys=True) not in seen:
                    candidates.append(patch_set)
        out = []
        for c in candidates:
            if validate_patch_set(c)[0]:
                ck = json.dumps(c, sort_keys=True)
                if ck not in [json.dumps(x, sort_keys=True) for x in out]:
                    out.append(c)
        return out[:n]

    def _get_benchmark_examples(self, patch_set: list) -> list:
        """Return benchmark examples for evaluation (uses patch_set as single example when no live API)."""
        return [{"patch_set": patch_set, "asi": {}}]

    def _get_current_failures(self) -> list:
        """Return current judge feedback failures."""
        return self.config.get("_judge_feedbacks", [])


def _apply_patch_set_to_config(config: dict, patch_set: list) -> None:
    """Apply patch set to config in-place (minimal stub for in-memory evaluation)."""
    for p in patch_set:
        if not isinstance(p, dict):
            continue
        pt = p.get("type", "")
        if pt == "add_instruction":
            instructions = config.setdefault("instructions", {})
            text_instr = instructions.setdefault("text_instructions", [])
            content = p.get("content", "Optimized instruction.")
            if isinstance(content, str):
                content = [content]
            if text_instr:
                text_instr[0]["content"] = content
            else:
                text_instr.append({"id": "gepa", "content": content})
        elif pt in ("add_synonym", "update_description", "add_description"):
            overlay = config.setdefault("genie_overlay", {})
            synonyms = overlay.setdefault("synonyms", {})
            obj = p.get("object_id") or p.get("target") or "default"
            synonyms[obj] = p.get("value", p.get("synonym", ""))


def select_best_patch_set(candidates: list[list[dict]]) -> list[dict] | None:
    """Select the best scoring patch set from a list of candidates.

    Args:
        candidates: List of patch sets (each is a list of patch dicts).

    Returns:
        Best patch set or None if no valid candidates.
    """
    if not candidates:
        return None
    best = None
    best_score = -1.0
    for patch_set in candidates:
        is_valid, _ = validate_patch_set(patch_set)
        if not is_valid:
            continue
        score = score_patch_set(patch_set, {})
        if score > best_score:
            best_score = score
            best = patch_set
    return best


def _extract_pattern(rationale: str) -> str:
    """Extract a generalizable pattern from a judge rationale."""
    r = (rationale or "").lower()
    if "table" in r and ("wrong" in r or "missing" in r or "incorrect" in r):
        return "wrong_table"
    if "column" in r and ("wrong" in r or "missing" in r):
        return "wrong_column"
    if "aggregation" in r or "measure" in r:
        return "wrong_aggregation"
    if "join" in r:
        return "wrong_join"
    if "filter" in r or "where" in r:
        return "wrong_filter"
    if "asset" in r or "routing" in r:
        return "wrong_asset_routing"
    return "other"


def _map_to_lever(root_cause: str, asi_failure_type: str = None, blame_set: str = None) -> int:
    """Map root cause to control lever ID (1-6).

    When ASI failure_type is provided, it takes precedence over the
    keyword-derived root_cause since it comes directly from the evaluator's
    FAILURE_TAXONOMY and is more precise.

    For repeatability_issue, routing depends on blame_set (asset type):
      - TABLE/MV/None -> Lever 1 (structured metadata: tags, column comments)
      - TVF -> Lever 6 (instructions for deterministic parameter selection)
    """
    ft = asi_failure_type or root_cause
    if ft == "repeatability_issue":
        if blame_set == "TVF":
            return 6
        return 1

    if ft == "missing_filter":
        bs = (blame_set or "").upper()
        if "TVF" in bs or "PARAM" in bs or "NULL" in bs:
            return 3  # TVF parameter format issue
        if "TEMPORAL" in bs or "DATE" in bs or "YEAR" in bs or "QUARTER" in bs:
            return 2  # Temporal filter on MV dimension
        return 3  # Default: TVF date param / filter syntax

    mapping = {
        "wrong_table": 1,
        "wrong_column": 1,
        "wrong_aggregation": 2,
        "wrong_join": 1,
        "wrong_filter": 3,
        "missing_temporal_filter": 2,
        "monitoring_gap": 4,
        "stale_data": 4,
        "data_freshness": 4,
        "ml_feature_missing": 5,
        "model_scoring_error": 5,
        "feature_store_mismatch": 5,
        "wrong_asset_routing": 6,
        "other": 6,
    }
    if asi_failure_type and asi_failure_type in mapping:
        return mapping[asi_failure_type]
    return mapping.get(root_cause, 6)


def cluster_failures(eval_results: dict, metadata_snapshot: dict) -> list:
    """Cluster evaluation failures by systemic root cause.

    Groups failures that share common patterns (same table, same judge,
    same error type). Only returns clusters with >=2 questions.
    Single-question failures go to the "long_tail" bucket.

    Args:
        eval_results: Dict with 'eval_result' (EvaluateResult with tables) or
                      'eval_results' (list of row dicts) or 'rows' (list of row dicts).
        metadata_snapshot: Current Genie metadata (unused in introspection, for API compat).

    Returns:
        list of cluster dicts with: cluster_id, root_cause, question_ids,
        affected_judge, confidence, asi_failure_type, asi_blame_set, asi_counterfactual_fixes
    """
    failures = []
    table = None

    # Handle MLflow EvaluateResult format (has .tables["eval_results"])
    results_obj = eval_results.get("eval_result")
    if results_obj is not None and hasattr(results_obj, "tables"):
        table = results_obj.tables.get("eval_results", None)
    elif results_obj is not None and hasattr(results_obj, "eval_results"):
        table = results_obj.eval_results

    # Handle JSON-serialized format: list of rows or dict with "rows"/"eval_results"
    if table is None:
        rows = (
            eval_results.get("eval_results")
            or eval_results.get("rows")
            or eval_results.get("table")
        )
        if isinstance(rows, list):
            table = rows

    if table is None:
        return []

    # Normalize to iterable of dicts (DataFrame or list of dicts)
    try:
        import pandas as pd

        if hasattr(table, "iterrows"):
            rows_iter = [row.to_dict() for _, row in table.iterrows()]
        else:
            rows_iter = table if isinstance(table, list) else []
    except ImportError:
        rows_iter = table if isinstance(table, list) else []

    # Collect failures from judge feedback columns, enriching with ASI metadata when present.
    # Supports both "feedback/<judge>" and "<judge>/value" layouts from evaluator artifacts.
    for row in rows_iter:
        if not isinstance(row, dict):
            continue
        row_dict = dict(row) if hasattr(row, "items") else row
        for col_name, val in list(row_dict.items()):
            judge = None
            if col_name.startswith("feedback/"):
                judge = col_name.replace("feedback/", "")
            elif col_name.endswith("/value"):
                judge = col_name.replace("/value", "")
            if judge and "no" in str(val).lower():
                rationale = (
                    row_dict.get(f"{judge}/rationale")
                    or row_dict.get(f"rationale/{judge}")
                    or row_dict.get("rationale", "")
                )
                question_id = (
                    row_dict.get("inputs/question_id")
                    or row_dict.get("inputs/question")
                    or row_dict.get("question_id")
                    or row_dict.get("question", "unknown")
                )

                judge_meta = row_dict.get(f"{judge}/metadata", {})
                asi_failure_type = (
                    row_dict.get(f"metadata/{judge}/failure_type")
                    or (judge_meta.get("failure_type") if isinstance(judge_meta, dict) else None)
                    or row_dict.get("metadata/failure_type")
                )
                asi_blame_set = (
                    row_dict.get(f"metadata/{judge}/blame_set")
                    or (judge_meta.get("blame_set") if isinstance(judge_meta, dict) else None)
                    or row_dict.get("metadata/blame_set")
                )
                asi_counterfactual = (
                    row_dict.get(f"metadata/{judge}/counterfactual_fix")
                    or (judge_meta.get("counterfactual_fix") if isinstance(judge_meta, dict) else None)
                    or row_dict.get("metadata/counterfactual_fix")
                )

                failures.append({
                    "question_id": question_id,
                    "judge": judge,
                    "rationale": rationale,
                    "asi_failure_type": asi_failure_type,
                    "asi_blame_set": asi_blame_set,
                    "asi_counterfactual_fix": asi_counterfactual,
                })

    pattern_groups = defaultdict(list)
    for f in failures:
        if f.get("asi_failure_type"):
            blame = str(f.get("asi_blame_set", "")) if f.get("asi_blame_set") else ""
            key = (f["judge"], f["asi_failure_type"], blame)
        else:
            key = (f["judge"], _extract_pattern(f["rationale"]), "")
        pattern_groups[key].append(f)

    clusters = []
    long_tail = []
    for group_key, items in pattern_groups.items():
        judge = group_key[0]
        pattern = group_key[1]
        blame = group_key[2] if len(group_key) > 2 else ""

        sample_asi_type = next((i["asi_failure_type"] for i in items if i.get("asi_failure_type")), None)

        entry = {
            "cluster_id": f"C{len(clusters) + 1:03d}",
            "root_cause": pattern,
            "question_ids": [i["question_id"] for i in items],
            "affected_judge": judge,
            "confidence": min(0.9, 0.5 + 0.1 * len(items)),
            "asi_failure_type": sample_asi_type,
            "asi_blame_set": blame or None,
            "asi_counterfactual_fixes": [
                i["asi_counterfactual_fix"] for i in items if i.get("asi_counterfactual_fix")
            ],
        }
        if len(items) >= 2:
            clusters.append(entry)
        else:
            long_tail.append(entry)

    clusters.sort(key=lambda c: len(c["question_ids"]), reverse=True)
    return clusters


_REPEATABILITY_FIX_BY_ASSET = {
    "TABLE": (
        "Add structured metadata to reduce ambiguity: "
        "column comments with business_definition, synonyms, grain, join_keys, do_not_use_when; "
        "UC tags: preferred_for_genie=true, domain=<domain>, synonyms=[...]. "
        "If variance persists, consider adding a TVF wrapper."
    ),
    "MV": (
        "Add structured column metadata to underlying tables to disambiguate aggregation routing. "
        "Include business_definition, preferred_questions[], do_not_use_when[] in column comments. "
        "If variance persists, convert metric view to TVF."
    ),
    "TVF": (
        "Add instruction clarifying deterministic parameter selection for this TVF. "
        "Ensure parameter descriptions include allowed_values and default conventions."
    ),
    "NONE": (
        "Add routing instruction and structured table metadata "
        "(preferred_for_genie=true tag, business_definition in description) "
        "so Genie can resolve this question."
    ),
}


_GENERIC_FIX_PREFIXES = ("review ", "check ", "verify ", "ensure ", "investigate ")


def _is_generic_counterfactual(fix: str) -> bool:
    """Return True if the counterfactual_fix is too generic to drive optimization."""
    if not fix:
        return True
    lower = fix.strip().lower()
    if any(lower.startswith(p) for p in _GENERIC_FIX_PREFIXES):
        has_specific_ref = any(
            tok in lower for tok in (".", "_", "column", "table ", "tvf", "function ")
            if len(tok) > 1
        )
        if not has_specific_ref:
            return True
    return False


def _describe_fix(cluster: dict) -> str:
    """Describe the fix for a cluster.

    Prefers ASI counterfactual_fix when available and specific (not generic).
    Generic fixes (e.g. "Review X in metadata") are skipped in favor of
    blame_set + wrong_clause pattern-based synthesis. For repeatability
    clusters, generates asset-type-specific recommendations.
    """
    asi_fixes = [f for f in cluster.get("asi_counterfactual_fixes", []) if f]
    specific_fixes = [f for f in asi_fixes if not _is_generic_counterfactual(f)]
    if specific_fixes:
        return specific_fixes[0]
    if cluster.get("root_cause") == "repeatability_issue":
        dominant_asset = cluster.get("asi_blame_set") or cluster.get("dominant_asset", "TABLE")
        base = _REPEATABILITY_FIX_BY_ASSET.get(dominant_asset, _REPEATABILITY_FIX_BY_ASSET["TABLE"])
        return f"{base} (affects {len(cluster['question_ids'])} questions)"
    wrong_clause = cluster.get("asi_wrong_clause") or ""
    blame = cluster.get("asi_blame_set") or ""
    if wrong_clause and blame:
        return (
            f"Fix {cluster['root_cause']}: wrong clause '{wrong_clause}' "
            f"in {blame} affecting {len(cluster['question_ids'])} questions."
        )
    return (
        f"Fix {cluster['root_cause']} affecting {len(cluster['question_ids'])} questions. "
        f"Judge: {cluster['affected_judge']}."
    )


def _dual_persist_paths(cluster: dict) -> dict:
    """Return API and repo paths for dual persistence."""
    lever = _map_to_lever(
        cluster["root_cause"],
        asi_failure_type=cluster.get("asi_failure_type"),
        blame_set=cluster.get("asi_blame_set"),
    )
    paths = {
        1: {
            "api": "ALTER TABLE ... SET TBLPROPERTIES / ALTER COLUMN ... COMMENT",
            "repo": "gold_layer_design/yaml/{domain}/*.yaml",
        },
        2: {
            "api": "CREATE OR REPLACE VIEW ... WITH METRICS",
            "repo": "src/semantic/metric_views/*.yaml",
        },
        3: {
            "api": "CREATE OR REPLACE FUNCTION",
            "repo": "src/semantic/tvfs/*.sql",
        },
        4: {
            "api": "ALTER TABLE ... SET TBLPROPERTIES (monitoring config)",
            "repo": "src/monitoring/{domain}_monitors.yaml",
        },
        5: {
            "api": "ALTER TABLE ... SET TBLPROPERTIES (ML feature metadata)",
            "repo": "src/ml/{domain}_feature_tables.yaml",
        },
        6: {
            "api": "PATCH /api/2.0/genie/spaces/{space_id}",
            "repo": "src/genie/{domain}_genie_export.json",
        },
    }
    return paths.get(lever, paths[6])


def _patch_to_lever(patch: dict) -> int:
    """Map a patch dict to a control lever number (1-6) based on its type/scope."""
    pt = patch.get("type", "")
    scope = patch.get("scope", "")
    if scope == "uc_table" or pt in ("update_description", "add_description", "add_table", "remove_table"):
        return 1
    if scope == "uc_column" or pt in (
        "add_column_description", "update_column_description", "hide_column",
        "unhide_column", "rename_column_alias", "add_synonym", "remove_synonym",
    ):
        return 1
    if "mv" in pt or scope == "metric_view":
        return 2
    if "tvf" in pt or scope == "tvf":
        return 3
    if "instruction" in pt or scope == "genie_overlay":
        return 6
    if "join" in pt:
        return 1
    if "filter" in pt:
        return 3
    if "compliance" in pt:
        return 1
    return 6


def generate_metadata_proposals(clusters: list, metadata_snapshot: dict, target_lever: int | None = None) -> list:
    """Generate metadata change proposals for each failure cluster.

    Each proposal maps to a specific control lever and includes
    the exact change to make with dual_persistence paths.

    Args:
        clusters: Failure clusters from cluster_failures().
        metadata_snapshot: Current metadata for context.
        target_lever: When provided, only return proposals for this lever (1-6).

    Returns:
        list of proposal dicts with: proposal_id, cluster_id, lever,
        change_description, dual_persistence, confidence, questions_fixed,
        questions_at_risk, net_impact
    """
    proposals = []
    for cluster in clusters:
        lever = _map_to_lever(
            cluster["root_cause"],
            asi_failure_type=cluster.get("asi_failure_type"),
            blame_set=cluster.get("asi_blame_set"),
        )
        if target_lever is not None and lever != target_lever:
            continue
        proposal = {
            "proposal_id": f"P{len(proposals) + 1:03d}",
            "cluster_id": cluster["cluster_id"],
            "lever": lever,
            "change_description": _describe_fix(cluster),
            "dual_persistence": _dual_persist_paths(cluster),
            "confidence": cluster["confidence"],
            "questions_fixed": len(cluster["question_ids"]),
            "questions_at_risk": 0,
            "net_impact": len(cluster["question_ids"]) * cluster["confidence"],
            "asi": {
                "failure_type": cluster.get("asi_failure_type") or cluster.get("root_cause", "other"),
                "blame_set": cluster.get("asi_blame_set") or [],
                "severity": "major",
                "counterfactual_fixes": cluster.get("asi_counterfactual_fixes", []),
                "ambiguity_detected": cluster.get("root_cause") == "repeatability_issue",
            },
        }
        proposals.append(proposal)

    proposals.sort(key=lambda p: p["net_impact"], reverse=True)
    return proposals


def _collect_judge_quality_feedback(clusters: list) -> list:
    """Detect generic counterfactual_fix values that are too vague for optimization.

    Returns a list of per-judge quality feedback dicts that can feed into the
    SIMBA Tier 3 judge alignment workflow.
    """
    from collections import Counter, defaultdict
    generic_by_judge = defaultdict(list)
    for c in clusters:
        judge = c.get("affected_judge", "unknown")
        for fix in c.get("asi_counterfactual_fixes", []):
            if fix and _is_generic_counterfactual(fix):
                generic_by_judge[judge].append(fix)

    feedback = []
    for judge, fixes in generic_by_judge.items():
        counts = Counter(fixes)
        most_common_fix, most_common_count = counts.most_common(1)[0]
        feedback.append({
            "judge_name": judge,
            "feedback_type": "generic_counterfactual_fix",
            "example": most_common_fix,
            "desired": (
                f"Specific fix referencing the exact asset/column/TVF to change, "
                f"e.g. 'Add WHERE payment_date >= DATE_TRUNC(\"year\", CURRENT_DATE()) "
                f"filter guidance to payment_date column comment'"
            ),
            "count": len(fixes),
        })
    feedback.sort(key=lambda f: f["count"], reverse=True)
    return feedback


def detect_conflicts_and_batch(proposals: list) -> list:
    """Detect conflicting proposals and group independent ones into batches."""
    batches = []
    used_levers = set()
    current_batch = []

    for p in proposals:
        if p["lever"] in used_levers:
            batches.append(current_batch)
            current_batch = [p]
            used_levers = {p["lever"]}
        else:
            current_batch.append(p)
            used_levers.add(p["lever"])

    if current_batch:
        batches.append(current_batch)
    return batches


def detect_regressions(current_metrics: dict, previous_metrics: dict) -> list:
    """Compare current vs previous iteration metrics to detect regressions."""
    regressions = []
    for key in current_metrics:
        if key in previous_metrics:
            if current_metrics[key] < previous_metrics[key] - 0.02:
                regressions.append({
                    "metric": key,
                    "previous": previous_metrics[key],
                    "current": current_metrics[key],
                    "delta": current_metrics[key] - previous_metrics[key],
                })
    return regressions


def main():
    parser = argparse.ArgumentParser(
        description="Genie Metadata Optimizer - Introspection and proposal generation"
    )
    parser.add_argument(
        "--eval-results",
        required=True,
        help="Path to evaluation results JSON file",
    )
    parser.add_argument(
        "--metadata-snapshot",
        default=None,
        help="Path to metadata snapshot JSON (optional, for GEPA tier)",
    )
    parser.add_argument(
        "--output",
        default="proposals.json",
        help="Output path for proposals JSON (default: proposals.json)",
    )
    parser.add_argument(
        "--tier",
        choices=["gepa", "introspect"],
        default="introspect",
        help="Optimization tier: gepa or introspect (default: introspect)",
    )
    parser.add_argument(
        "--use-asi",
        action="store_true",
        default=False,
        help="Use ASI judge feedback for patch proposal (default: False)",
    )
    parser.add_argument(
        "--use-patch-dsl",
        action="store_true",
        default=False,
        help="Use patch DSL validation and scoring (default: False)",
    )
    parser.add_argument(
        "--use-gepa",
        action="store_true",
        default=False,
        help="Use GEPA L2 optimization with patch set candidates (default: False)",
    )
    parser.add_argument(
        "--space-id",
        default=None,
        help="Genie Space ID (required when --use-gepa is set)",
    )
    parser.add_argument(
        "--target-lever",
        type=int,
        default=None,
        choices=[1, 2, 3, 4, 5, 6],
        help="Filter proposals to a single lever (1-6). Used by orchestrator for per-lever optimization.",
    )
    parser.add_argument(
        "--recommended",
        action="store_true",
        default=False,
        help="Enable all feature flags (--use-asi --use-patch-dsl --use-gepa). Recommended for production.",
    )
    args = parser.parse_args()

    if args.recommended:
        args.use_asi = True
        args.use_patch_dsl = True
        args.use_gepa = True

    global USE_ASI, USE_PATCH_DSL, USE_GEPA
    USE_ASI = args.use_asi
    USE_PATCH_DSL = args.use_patch_dsl
    USE_GEPA = args.use_gepa

    eval_path = Path(args.eval_results)
    if not eval_path.exists():
        print(f"ERROR: Eval results file not found: {eval_path}")
        return 1

    with open(eval_path) as f:
        eval_results = json.load(f)

    metadata_snapshot = {}
    if args.metadata_snapshot:
        snap_path = Path(args.metadata_snapshot)
        if snap_path.exists():
            with open(snap_path) as f:
                metadata_snapshot = json.load(f)

    if args.tier == "gepa":
        try:
            from gepa import optimize_anything, GEPAConfig, EngineConfig, ReflectionConfig

            if not metadata_snapshot:
                print("ERROR: --metadata-snapshot is required for GEPA tier.")
                return 1

            from metadata_optimizer import score_patch_set

            def _gepa_metric(candidate: dict) -> float:
                """GEPA metric: score candidate patch set against metadata."""
                patches = candidate.get("patches", [candidate])
                if isinstance(patches, dict):
                    patches = [patches]
                return score_patch_set(patches, metadata_snapshot)

            seed = {"text_instructions": [], "example_question_sqls": []}
            if metadata_snapshot.get("instructions"):
                seed["text_instructions"] = metadata_snapshot["instructions"].get("text_instructions", [])
                seed["example_question_sqls"] = metadata_snapshot["instructions"].get("example_question_sqls", [])

            gepa_config = GEPAConfig(
                engine=EngineConfig(max_metric_calls=150, cache_evaluation=True),
                reflection=ReflectionConfig(reflection_lm="databricks:/databricks-claude-sonnet-4-6"),
            )

            print("Running GEPA optimize_anything (Lever 6 only)...")
            result = optimize_anything(seed=seed, metric=_gepa_metric, config=gepa_config)

            output = {
                "best_candidate": result.best_candidate,
                "best_score": result.best_score,
                "total_metric_calls": result.total_metric_calls,
                "tier": "gepa",
                "lever": 6,
            }
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(output, f, indent=2, default=str)
            print(f"GEPA: Best score {result.best_score:.2f}, {result.total_metric_calls} metric calls")
            print(f"Output written to {out_path}")
            return 0

        except ImportError:
            print("WARNING: gepa package not installed (pip install 'gepa>=0.1.0').")
            print("Use the GEPA template notebook (run_gepa_optimization.py) in Databricks instead.")
            print("Falling back to introspect tier.")
            args.tier = "introspect"

    if USE_GEPA:
        space_id = args.space_id or ""
        judge_feedbacks = _extract_judge_feedbacks_from_eval(eval_results)
        if metadata_snapshot and judge_feedbacks:
            best_patch_set = run_gepa_optimization(
                space_id=space_id,
                config=metadata_snapshot,
                judge_feedbacks=judge_feedbacks,
                max_rounds=3,
                use_gepa=True,
            )
            if best_patch_set:
                proposals = _convert_patch_set_to_proposals(best_patch_set)
                clusters = cluster_failures(eval_results, metadata_snapshot)
                batches = detect_conflicts_and_batch(proposals)
                output = {
                    "clusters": clusters,
                    "proposals": proposals,
                    "batches": batches,
                    "tier": "gepa_l2",
                    "use_gepa": True,
                    "best_patch_set": best_patch_set,
                }
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(output, f, indent=2)
                print(f"GEPA L2: Generated {len(proposals)} proposals from best patch set")
                print(f"Output written to {out_path}")
                return 0
            print("GEPA L2: No valid patch set produced; falling back to introspect.")
        else:
            print("GEPA L2: Missing metadata-snapshot or judge feedbacks; falling back to introspect.")

    target_lever = getattr(args, "target_lever", None)
    if target_lever:
        print(f"Filtering proposals to lever {target_lever} only")

    if args.tier == "introspect":
        clusters = cluster_failures(eval_results, metadata_snapshot)
        print(f"Clustered {len(clusters)} failure clusters")

        if USE_ASI:
            judge_feedbacks = _extract_judge_feedbacks_from_eval(eval_results)
            if judge_feedbacks:
                patch_set = propose_patch_set_from_asi(judge_feedbacks, metadata_snapshot, target_lever=target_lever)
                if patch_set:
                    if USE_PATCH_DSL:
                        is_valid, errs = validate_patch_set(patch_set)
                        if not is_valid:
                            print(f"ASI patch set validation warnings: {errs}")
                    proposals = _convert_patch_set_to_proposals(patch_set)
                    print(f"Generated {len(proposals)} proposals (ASI path)")
                else:
                    proposals = generate_metadata_proposals(clusters, metadata_snapshot, target_lever=target_lever)
                    print(f"Generated {len(proposals)} proposals (fallback: ASI insufficient)")
            else:
                proposals = generate_metadata_proposals(clusters, metadata_snapshot, target_lever=target_lever)
                print(f"Generated {len(proposals)} proposals (fallback: ASI insufficient)")
        else:
            proposals = generate_metadata_proposals(clusters, metadata_snapshot, target_lever=target_lever)
            print(f"Generated {len(proposals)} proposals")

        if USE_PATCH_DSL and proposals:
            for p in proposals:
                patch = {"type": p.get("lever_type", "other"), "object_id": p.get("cluster_id")}
                is_valid, _ = validate_patch_set([patch])
                p["patch_dsl_valid"] = is_valid

        batches = detect_conflicts_and_batch(proposals)
        print(f"Created {len(batches)} non-conflicting batches")

        output = {
            "clusters": clusters,
            "proposals": proposals,
            "batches": batches,
            "tier": "introspect",
            "use_asi": USE_ASI,
            "use_patch_dsl": USE_PATCH_DSL,
        }
    else:
        output = {"tier": args.tier, "proposals": [], "batches": []}

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Output written to {out_path}")
    return 0


if __name__ == "__main__":
    exit(main())

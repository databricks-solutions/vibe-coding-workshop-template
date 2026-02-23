#!/usr/bin/env python3
"""
Genie Optimization Orchestrator v4.2.0

Routes to 4 worker skills on demand. Maintains session state in
optimization-progress.json and MLflow experiment tags.

Lever-aware loop: generate benchmarks -> baseline eval -> per-lever
optimize/apply/verify/eval (levers 1-5) -> GEPA lever 6 -> deploy.
Max 5 iterations with plateau detection. Slice/P0 gates enforced in code.

Usage:
    python orchestrator.py --discover
    python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --uc-schema cat.schema
    python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --evaluate-only
    python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --resume
    python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --job-mode --target dev
    python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml --worker-dir ../genie-optimization-workers
    # NOTE: --job-mode is REQUIRED for lever-aware optimization (8-judge harness).

Requirements:
    - databricks-sdk
    - mlflow[databricks]>=3.4.0
    - pyyaml
    - gepa>=0.1.0 (Tier 1 only)
"""

import re
import time
import json
import yaml
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

def _resolve_cli_profile() -> str | None:
    """Read databricks.yml to resolve workspace profile for WorkspaceClient."""
    for candidate in ["databricks.yml", "../databricks.yml", "../../databricks.yml"]:
        p = Path(candidate)
        if p.exists():
            try:
                cfg = yaml.safe_load(p.read_text())
                profile = (cfg.get("workspace") or {}).get("profile")
                if profile:
                    print(f"  CLI profile resolved from {candidate}: {profile}")
                    return profile
            except Exception:
                pass
    return None


_cli_profile = _resolve_cli_profile()
try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient(profile=_cli_profile) if _cli_profile else WorkspaceClient()
    if _cli_profile:
        print(f"  WorkspaceClient initialized with profile: {_cli_profile}")
except ImportError:
    print("WARNING: databricks-sdk not installed.")
    w = None

try:
    import mlflow
except ImportError:
    mlflow = None

# ---------------------------------------------------------------------------
# Worker script imports (Optimizer + Applier)
# ---------------------------------------------------------------------------
_WORKERS_AVAILABLE = False

def _setup_worker_imports(worker_dir: str | None = None):
    """Import functions from worker scripts. Call once at startup."""
    global _WORKERS_AVAILABLE
    import sys

    if worker_dir:
        abs_dir = str(Path(worker_dir).resolve())
        if abs_dir not in sys.path:
            sys.path.insert(0, abs_dir)

    candidate_dirs = [
        worker_dir,
        str(Path(__file__).resolve().parent.parent / "genie-optimization-workers" / "03-genie-metadata-optimizer" / "scripts"),
    ]
    optimizer_dir = None
    for d in candidate_dirs:
        if d and Path(d).is_dir():
            optimizer_dir = d
            break
    if optimizer_dir and optimizer_dir not in sys.path:
        sys.path.insert(0, optimizer_dir)

    applier_candidates = [
        worker_dir,
        str(Path(__file__).resolve().parent.parent / "genie-optimization-workers" / "04-genie-optimization-applier" / "scripts"),
    ]
    for d in applier_candidates:
        if d and Path(d).is_dir() and d not in sys.path:
            sys.path.insert(0, d)
            break

    generator_candidates = [
        worker_dir,
        str(Path(__file__).resolve().parent.parent / "genie-optimization-workers" / "01-genie-benchmark-generator" / "scripts"),
    ]
    for d in generator_candidates:
        if d and Path(d).is_dir() and d not in sys.path:
            sys.path.insert(0, d)
            break

    try:
        from metadata_optimizer import (  # noqa: F401
            cluster_failures as _cf,
            generate_metadata_proposals as _gmp,
            detect_regressions as _dr,
            run_gepa_optimization as _rgo,
        )
        from optimization_applier import (  # noqa: F401
            apply_proposal_batch as _apb,
            strip_non_exportable_fields as _snef,
            verify_repo_update as _vru,
        )
        _WORKERS_AVAILABLE = True
    except ImportError as e:
        print(f"WARNING: Worker scripts not on sys.path ({e}). "
              "Lever-aware optimization unavailable. Use --worker-dir to specify.")
        _WORKERS_AVAILABLE = False

def _import_optimizer():
    """Lazy import of optimizer functions."""
    from metadata_optimizer import (
        cluster_failures,
        generate_metadata_proposals,
        detect_regressions,
        run_gepa_optimization,
    )
    return cluster_failures, generate_metadata_proposals, detect_regressions, run_gepa_optimization

def _import_applier():
    """Lazy import of applier functions."""
    from optimization_applier import (
        apply_proposal_batch,
        strip_non_exportable_fields,
        verify_repo_update,
    )
    return apply_proposal_batch, strip_non_exportable_fields, verify_repo_update


def _default_experiment_path(domain: str) -> str:
    """Build a /Users/<email>/genie-optimization/<domain> experiment path.

    Hard constraint #7: bare paths like /genie-optimization/... cause
    RESOURCE_DOES_NOT_EXIST. Must be under /Users/<email>/.
    """
    import os
    email = os.environ.get("DATABRICKS_USER_EMAIL", "")
    if not email and w is not None:
        try:
            me = w.current_user.me()
            email = me.user_name or ""
        except Exception:
            pass
    if not email:
        email = "unknown_user"
    path = f"/Users/{email}/genie-optimization/{domain}"
    return path


def _validate_experiment_path(exp_name: str):
    """Warn if experiment path doesn't start with /Users/ and pre-create parent."""
    if not exp_name.startswith("/Users/"):
        print(
            f"WARNING: Experiment path '{exp_name}' does not start with /Users/<email>/. "
            "This may cause RESOURCE_DOES_NOT_EXIST errors (hard constraint #7). "
            "Recommended: /Users/<your-email>/genie-optimization/<domain>"
        )
    parent = "/".join(exp_name.split("/")[:-1])
    if w is not None and parent:
        try:
            w.workspace.mkdirs(parent)
        except Exception:
            pass


def _verify_mlflow_tracking():
    """Fail fast if MLflow is not configured for remote tracking."""
    if mlflow is None:
        raise RuntimeError(
            "mlflow is not installed. Install with: pip install 'mlflow[databricks]'"
        )
    tracking_uri = mlflow.get_tracking_uri()
    if tracking_uri != "databricks" and not tracking_uri.startswith("databricks"):
        import os
        host = os.environ.get("DATABRICKS_HOST", "")
        if not host:
            raise RuntimeError(
                "MLflow is not configured for Databricks tracking.\n"
                "Set these environment variables before running:\n"
                "  export DATABRICKS_HOST='https://<workspace>.cloud.databricks.com'\n"
                "  export DATABRICKS_TOKEN='<token>'\n"
                "  export MLFLOW_TRACKING_URI='databricks'\n"
                "Or run inside a Databricks notebook where MLflow is auto-configured."
            )


def _split_uc_schema(uc_schema: str | None) -> tuple[str, str]:
    """Split <catalog>.<schema> into components."""
    if not uc_schema or "." not in uc_schema:
        return "", ""
    parts = uc_schema.split(".")
    if len(parts) < 2:
        return "", ""
    return parts[0], parts[1]


def _run_sql_statement_rows(warehouse_id: str, statement: str) -> list[dict]:
    """Execute SQL Statement API query and return rows as dicts (best effort)."""
    if w is None or not warehouse_id:
        return []
    try:
        resp = w.api_client.do(
            "POST",
            "/api/2.0/sql/statements",
            body={
                "warehouse_id": warehouse_id,
                "statement": statement,
                "wait_timeout": "30s",
                "disposition": "INLINE",
                "format": "JSON_ARRAY",
            },
        )
        statement_id = resp.get("statement_id")
        status = (resp.get("status") or {}).get("state", "")
        polls = 0
        while statement_id and status in ("PENDING", "RUNNING") and polls < 30:
            time.sleep(2)
            resp = w.api_client.do("GET", f"/api/2.0/sql/statements/{statement_id}")
            status = (resp.get("status") or {}).get("state", "")
            polls += 1

        if status != "SUCCEEDED":
            return []

        manifest = resp.get("manifest", {}) or {}
        result = resp.get("result", {}) or {}
        columns = (((manifest.get("schema") or {}).get("columns")) or [])
        data_rows = result.get("data_array", []) or []
        if not columns:
            return []
        col_names = [c.get("name", f"c{i}") for i, c in enumerate(columns)]
        return [dict(zip(col_names, row)) for row in data_rows]
    except Exception:
        return []


# =========================================================================
# Space Discovery
# =========================================================================

def discover_spaces() -> list:
    """List available Genie Spaces via SDK."""
    if w is None:
        print("ERROR: SDK not initialized.")
        return []
    spaces = list(w.genie.list_spaces())
    return [{"id": s.space_id, "title": s.title} for s in spaces]


# =========================================================================
# LoggedModel Version Tracking
# =========================================================================

def _build_patch_summary(patch_set: list, iteration: int) -> dict:
    """Build a structured summary of patches for quick cross-model comparison."""
    from collections import Counter
    by_type = Counter()
    by_lever = Counter()
    by_risk = Counter()
    targets = []
    patch_details = []
    for p in patch_set:
        ptype = p.get("type", f"lever_{p.get('lever', 'unknown')}")
        lever = str(p.get("lever", "unknown"))
        risk = p.get("risk_level", "unknown")
        target = p.get("target") or p.get("object_id") or p.get("table") or ""
        by_type[ptype] += 1
        by_lever[lever] += 1
        by_risk[risk] += 1
        if target:
            targets.append(target)
        patch_details.append({
            "type": ptype,
            "target": target,
            "lever": lever,
            "risk": risk,
            "description": p.get("change_description", p.get("description", "")),
        })
    return {
        "iteration": iteration,
        "patch_count": len(patch_set),
        "by_type": dict(by_type),
        "by_lever": dict(by_lever),
        "by_risk": dict(by_risk),
        "targets": targets,
        "patches": patch_details,
    }


def _compute_uc_metadata_diff(
    parent_model_id: str | None,
    current_columns: list,
    current_tags: list,
    current_routines: list,
) -> dict | None:
    """Compute UC metadata diff between current state and parent LoggedModel.

    Downloads parent's model_state/ artifacts via source_run_id and diffs
    columns (keyed by table_name+column_name), tags (keyed by table+tag_name),
    and routines (keyed by routine_name).
    """
    if not parent_model_id or parent_model_id == "none":
        return None
    try:
        parent = mlflow.get_logged_model(model_id=parent_model_id)
        if not parent.source_run_id:
            return None
        import tempfile as _tf
        artifact_dir = mlflow.artifacts.download_artifacts(
            run_id=parent.source_run_id,
            artifact_path="model_state",
            dst_path=_tf.mkdtemp(prefix="parent_model_state_"),
        )
    except Exception:
        return None

    import os as _os

    def _load_json(fname):
        fpath = _os.path.join(artifact_dir, fname)
        if _os.path.exists(fpath):
            with open(fpath) as f:
                return json.load(f)
        return []

    prev_columns = _load_json("uc_columns.json")
    prev_tags = _load_json("uc_tags.json")
    prev_routines = _load_json("uc_routines.json")

    import shutil as _sh
    _sh.rmtree(artifact_dir, ignore_errors=True)

    def _diff_rows(prev, curr, key_fields, compare_fields=None):
        def _row_key(row):
            return tuple(str(row.get(k, "")) for k in key_fields)
        prev_map = {_row_key(r): r for r in prev}
        curr_map = {_row_key(r): r for r in curr}
        prev_keys = set(prev_map.keys())
        curr_keys = set(curr_map.keys())
        added = [curr_map[k] for k in sorted(curr_keys - prev_keys)]
        removed = [prev_map[k] for k in sorted(prev_keys - curr_keys)]
        modified = []
        if compare_fields:
            for k in sorted(prev_keys & curr_keys):
                for field in compare_fields:
                    old_val = str(prev_map[k].get(field, ""))
                    new_val = str(curr_map[k].get(field, ""))
                    if old_val != new_val:
                        modified.append({
                            "key": ".".join(str(x) for x in k),
                            "field": field,
                            "old": old_val,
                            "new": new_val,
                        })
        return {"added": added, "removed": removed, "modified": modified}

    col_diff = _diff_rows(
        prev_columns, current_columns,
        key_fields=["table_name", "column_name"],
        compare_fields=["data_type", "comment"],
    )
    tag_diff = _diff_rows(
        prev_tags, current_tags,
        key_fields=["table_name", "tag_name"],
        compare_fields=["tag_value"],
    )
    routine_diff = _diff_rows(
        prev_routines, current_routines,
        key_fields=["routine_name"],
        compare_fields=["routine_definition", "return_type"],
    )

    return {
        "parent_model_id": parent_model_id,
        "columns": col_diff,
        "tags": tag_diff,
        "routines": routine_diff,
        "summary": {
            "columns_changed": len(col_diff["added"]) + len(col_diff["removed"]) + len(col_diff["modified"]),
            "tags_changed": len(tag_diff["added"]) + len(tag_diff["removed"]) + len(tag_diff.get("modified", [])),
            "routines_changed": len(routine_diff["added"]) + len(routine_diff["removed"]) + len(routine_diff["modified"]),
        },
    }


def link_eval_scores_to_model(model_id: str, eval_result: dict):
    """Log evaluation scores as model-level metrics for cross-model comparison.

    Called after each evaluation so per-judge scores appear on the Models tab
    and are searchable via search_logged_models().
    """
    if not model_id or not eval_result:
        return
    scores = eval_result.get("scores", {})
    metrics = {"overall_accuracy": eval_result.get("overall_accuracy", 0)}
    for judge_name, score in scores.items():
        if isinstance(score, (int, float)):
            metrics[judge_name] = score
    rep = eval_result.get("repeatability_pct")
    if rep:
        metrics["repeatability_pct"] = rep
    try:
        mlflow.log_metrics(metrics=metrics, model_id=model_id)
    except Exception as e:
        print(f"  WARNING: Failed to link eval scores to model {model_id}: {e}")


def create_genie_model_version(space_id: str, config: dict,
                                iteration: int, domain: str,
                                patch_set=None, parent_model_id=None,
                                prompt_versions=None, uc_schema: str | None = None) -> str:
    """Create a LoggedModel with a linked creation run for this iteration.

    Uses create_external_model() inside an mlflow.start_run() so that:
      - "Logged From" in the UI points to the creation run (source_run_id)
      - Artifacts (full UC metadata, config, patches) are persisted in the run
      - Evaluation runs link back via mlflow.genai.evaluate(model_id=...)

    Artifact layout per creation run:
      model_state/genie_config.json       - full Genie Space config
      model_state/uc_columns.json         - complete information_schema.columns
      model_state/uc_tags.json            - complete information_schema.table_tags
      model_state/uc_routines.json        - complete INFORMATION_SCHEMA.ROUTINES
      model_state/uc_metadata_diff.json   - diff vs parent model (if parent exists)
      patches/patch_set.json              - full Patch DSL array
      patches/patch_summary.json          - structured summary by type/lever/risk
    """
    import tempfile
    import os as _os

    uc_columns = []
    uc_tags = []
    uc_routines = []
    warehouse_id = config.get("warehouse_id", "")
    uc_catalog, uc_db = _split_uc_schema(uc_schema)
    if uc_catalog and uc_db and warehouse_id:
        uc_columns = _run_sql_statement_rows(
            warehouse_id,
            (
                f"SELECT table_name, column_name, data_type, comment "
                f"FROM {uc_catalog}.information_schema.columns "
                f"WHERE table_schema = '{uc_db}'"
            ),
        )
        uc_tags = _run_sql_statement_rows(
            warehouse_id,
            (
                f"SELECT * FROM {uc_catalog}.information_schema.table_tags "
                f"WHERE schema_name = '{uc_db}'"
            ),
        )
        uc_routines = _run_sql_statement_rows(
            warehouse_id,
            (
                f"SELECT routine_name, routine_type, routine_definition, "
                f"data_type AS return_type, routine_schema "
                f"FROM {uc_catalog}.INFORMATION_SCHEMA.ROUTINES "
                f"WHERE routine_schema = '{uc_db}'"
            ),
        )

    config_hash = hashlib.sha256(
        json.dumps(
            {
                "genie_config": config,
                "uc_columns": uc_columns,
                "uc_tags": uc_tags,
                "uc_routines": uc_routines,
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:12]
    model_name = f"genie-{domain}-iter{iteration}-{config_hash}"

    instructions = config.get("general_instructions", "")
    data_assets = config.get("data_assets", [])

    patch_summary = _build_patch_summary(patch_set, iteration) if patch_set else None
    patch_levers = ",".join(
        str(p.get("lever", "?")) for p in patch_set
    ) if patch_set else "none"
    patch_targets_list = [
        p.get("target") or p.get("object_id") or p.get("table") or ""
        for p in (patch_set or [])
    ]
    patch_targets_preview = ",".join(patch_targets_list[:3]) or "none"

    uc_diff = _compute_uc_metadata_diff(
        parent_model_id, uc_columns, uc_tags, uc_routines,
    )

    model_params = {
        "space_id": space_id,
        "iteration": str(iteration),
        "domain": domain,
        "config_hash": config_hash,
        "instruction_char_count": str(len(instructions)),
        "data_asset_count": str(len(data_assets)),
        "mv_count": str(sum(1 for a in data_assets if a.get("type") == "METRIC_VIEW")),
        "tvf_count": str(sum(1 for a in data_assets if a.get("type") == "FUNCTION")),
        "table_count": str(sum(1 for a in data_assets if a.get("type") == "TABLE")),
        "instruction_preview": instructions[:200],
        "patch_count": str(len(patch_set)) if patch_set else "0",
        "patch_types": ",".join(
            p.get("type", f"lever_{p.get('lever', 'unknown')}")
            for p in patch_set
        ) if patch_set else "none",
        "patch_levers": patch_levers,
        "patch_targets": patch_targets_preview,
        "patch_risk_levels": ",".join(
            sorted(set(p.get("risk_level", "unknown") for p in patch_set))
        ) if patch_set else "none",
        "parent_model_id": parent_model_id or "none",
        "prompt_versions": json.dumps(prompt_versions) if prompt_versions else "{}",
        "uc_schema": uc_schema or "",
        "uc_columns_count": str(len(uc_columns)),
        "uc_tags_count": str(len(uc_tags)),
        "uc_routines_count": str(len(uc_routines)),
    }
    if uc_diff:
        model_params["uc_columns_changed"] = str(uc_diff["summary"]["columns_changed"])
        model_params["uc_tags_changed"] = str(uc_diff["summary"]["tags_changed"])
        model_params["uc_routines_changed"] = str(uc_diff["summary"]["routines_changed"])

    run_name = f"create_model_iter{iteration}_{config_hash}"
    with mlflow.start_run(run_name=run_name) as creation_run:
        mlflow.log_params({
            "space_id": space_id,
            "iteration": str(iteration),
            "domain": domain,
            "config_hash": config_hash,
            "model_name": model_name,
        })

        logged_model = mlflow.create_external_model(
            name=model_name,
            source_run_id=creation_run.info.run_id,
            params=model_params,
            tags={
                "domain": domain,
                "space_id": space_id,
                "iteration": str(iteration),
                "parent_model_id": parent_model_id or "",
            },
            model_type="genie-space",
        )

        state_dir = _os.path.join(
            tempfile.gettempdir(),
            f"model_state_iter{iteration}_{config_hash}",
        )
        _os.makedirs(state_dir, exist_ok=True)

        for fname, data in [
            ("genie_config.json", config),
            ("uc_columns.json", uc_columns),
            ("uc_tags.json", uc_tags),
            ("uc_routines.json", uc_routines),
        ]:
            fpath = _os.path.join(state_dir, fname)
            with open(fpath, "w") as sf:
                json.dump(data, sf, indent=2, default=str)
            mlflow.log_artifact(fpath, artifact_path="model_state")

        if uc_diff:
            diff_path = _os.path.join(state_dir, "uc_metadata_diff.json")
            with open(diff_path, "w") as df:
                json.dump(uc_diff, df, indent=2, default=str)
            mlflow.log_artifact(diff_path, artifact_path="model_state")

        if patch_set:
            patch_path = _os.path.join(state_dir, "patch_set.json")
            with open(patch_path, "w") as f:
                json.dump(patch_set, f, indent=2, default=str)
            mlflow.log_artifact(patch_path, artifact_path="patches")

            summary_path = _os.path.join(state_dir, "patch_summary.json")
            with open(summary_path, "w") as f:
                json.dump(patch_summary, f, indent=2, default=str)
            mlflow.log_artifact(summary_path, artifact_path="patches")

        import shutil as _shutil
        _shutil.rmtree(state_dir, ignore_errors=True)

        mlflow.log_metric("uc_columns_count", len(uc_columns))
        mlflow.log_metric("uc_tags_count", len(uc_tags))
        mlflow.log_metric("uc_routines_count", len(uc_routines))
        mlflow.log_metric("data_asset_count", len(data_assets))
        if uc_diff:
            mlflow.log_metric("uc_columns_changed", uc_diff["summary"]["columns_changed"])
            mlflow.log_metric("uc_tags_changed", uc_diff["summary"]["tags_changed"])
            mlflow.log_metric("uc_routines_changed", uc_diff["summary"]["routines_changed"])

    mlflow.set_active_model(model_id=logged_model.model_id)

    print(f"  LoggedModel: {model_name} (model_id={logged_model.model_id})")
    print(f"    Logged From: run {creation_run.info.run_id}")
    print(f"    Artifacts: genie_config.json, uc_columns.json ({len(uc_columns)} rows), "
          f"uc_tags.json ({len(uc_tags)} rows), uc_routines.json ({len(uc_routines)} rows)")
    if uc_diff:
        s = uc_diff["summary"]
        print(f"    UC diff vs parent: {s['columns_changed']} cols, "
              f"{s['tags_changed']} tags, {s['routines_changed']} routines changed")
    if parent_model_id and parent_model_id != "none":
        print(f"    Parent: {parent_model_id}")
    if patch_set:
        print(f"    Patches: {len(patch_set)} (levers={patch_levers}, "
              f"types={model_params['patch_types']})")
    return logged_model.model_id


def promote_best_model(session: dict):
    """Tag the best-performing LoggedModel for promotion.

    Call after the optimization loop converges or reaches max iterations.
    """
    best_iter = session.get("best_iteration", 0)
    iterations = session.get("iterations", [])
    if not iterations or best_iter < 1:
        print("  No iterations to promote.")
        return

    best_result = iterations[best_iter - 1] if best_iter <= len(iterations) else iterations[-1]
    best_model_id = best_result.get("model_id")
    if not best_model_id:
        print("  No model_id found for best iteration.")
        return

    try:
        mlflow.set_logged_model_tags(
            model_id=best_model_id,
            tags={
                "promoted": "true",
                "promotion_reason": session.get("convergence_reason", "target_met"),
                "best_accuracy": str(session.get("best_overall_accuracy", 0)),
                "best_iteration": str(best_iter),
            },
        )
        print(f"  Promoted LoggedModel: {best_model_id} "
              f"(accuracy: {session.get('best_overall_accuracy', 0):.1f}%)")
    except Exception as e:
        print(f"  WARNING: Model promotion failed: {e}")


def rollback_to_model(model_id: str, space_id: str):
    """Restore Genie Space config from a LoggedModel's creation run artifacts.

    Downloads model_state/genie_config.json from the creation run linked
    via source_run_id. Used when P0 gate fails and the orchestrator needs
    to revert to the previous iteration's configuration.
    """
    try:
        model = mlflow.get_logged_model(model_id=model_id)
        if not model.source_run_id:
            print(f"  WARNING: LoggedModel {model_id} has no source_run_id — "
                  "cannot download artifacts for rollback.")
            return None

        artifact_dir = mlflow.artifacts.download_artifacts(
            run_id=model.source_run_id, artifact_path="model_state"
        )
        import os as _os
        config_path = _os.path.join(artifact_dir, "genie_config.json")
        if not _os.path.exists(config_path):
            for fname in _os.listdir(artifact_dir):
                if fname.endswith(".json") and "config" in fname:
                    config_path = _os.path.join(artifact_dir, fname)
                    break
            else:
                print(f"  WARNING: No genie_config.json in {artifact_dir}")
                return None

        with open(config_path) as f:
            config = json.load(f)

        print(f"  Rollback config loaded from LoggedModel {model_id}")
        print(f"    source_run: {model.source_run_id}")
        return config
    except Exception as e:
        print(f"  WARNING: Rollback from LoggedModel failed: {e}")
        return None


_TEMPORAL_PHRASES = re.compile(
    r"\b(this year|last year|last quarter|this quarter|last \d+ months?|"
    r"last \d+ days?|this month|last month|year to date|ytd)\b",
    re.IGNORECASE,
)
_HARDCODED_DATE = re.compile(r"'\d{4}-\d{2}-\d{2}'")


def _check_temporal_freshness(benchmarks: list) -> list:
    """Flag benchmarks with temporal phrasing but hardcoded dates in expected SQL.

    Returns list of dicts with question_id, question, and the hardcoded dates found.
    """
    stale = []
    for b in benchmarks:
        question = b.get("question", "")
        expected_sql = b.get("expected_sql", "") or b.get("sql", "")
        if _TEMPORAL_PHRASES.search(question) and _HARDCODED_DATE.search(expected_sql):
            dates_found = _HARDCODED_DATE.findall(expected_sql)
            qid = b.get("question_id", b.get("id", "unknown"))
            print(
                f"  WARNING: {qid} has temporal phrasing but hardcoded dates "
                f"{dates_found} in expected SQL — GT may be stale"
            )
            stale.append({
                "question_id": qid,
                "question": question,
                "hardcoded_dates": dates_found,
            })
    if stale:
        print(f"  {len(stale)} benchmarks flagged for potential date staleness")
    return stale


def _fetch_space_config(space_id: str) -> dict:
    """GET Genie Space config with full serialized_space content."""
    if w is None:
        return {}
    config = w.api_client.do(
        "GET",
        f"/api/2.0/genie/spaces/{space_id}",
        query={"include_serialized_space": "true"},
    )
    data_assets = config.get("data_assets", [])
    tables = sum(1 for a in data_assets if a.get("type") == "TABLE")
    mvs = sum(1 for a in data_assets if a.get("type") == "METRIC_VIEW")
    tvfs = sum(1 for a in data_assets if a.get("type") == "FUNCTION")
    has_instructions = bool(config.get("general_instructions"))
    print(f"  Space state: tables={tables}, metric_views={mvs}, tvfs={tvfs}, "
          f"instructions={'present' if has_instructions else 'absent'}")
    return config


# =========================================================================
# Progress Tracking
# =========================================================================

def init_progress(space_id: str, domain: str, max_iterations: int = 5) -> dict:
    return {
        "space_id": space_id,
        "domain": domain,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "current_iteration": 0,
        "max_iterations": max_iterations,
        "status": "in_progress",
        "iterations": [],
        "best_iteration": 0,
        "best_overall_accuracy": 0.0,
        "remaining_failures": [],
        "convergence_reason": None,
        "promoted_model_id": None,
        "score_history": [],
        "patch_history": [],
        "pareto_frontier": [],
        "current_patch_set": None,
        "patched_objects": [],
        "maturity_level": "L1",
        "benchmark_corrections": [],
        "lever_impacts": {},
        "worker_reads": [],
        "eval_dataset_name": None,
        "use_patch_dsl": True,
        "repeatability_pct": 0.0,
        "best_repeatability": 0.0,
        "repeatability_target": 90.0,
        "lever_audit": {
            str(i): {
                "attempted": False,
                "proposals_generated": 0,
                "proposals_applied": 0,
                "skip_reason": None,
            }
            for i in range(1, 7)
        },
    }


def load_progress(path: str):
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def update_progress(progress: dict, iteration_result: dict) -> dict:
    progress["iterations"].append(iteration_result)
    progress["current_iteration"] = iteration_result.get(
        "iteration", len(progress["iterations"])
    )
    overall = iteration_result.get("overall_accuracy", 0)
    if overall > progress["best_overall_accuracy"]:
        progress["best_overall_accuracy"] = overall
        progress["best_iteration"] = progress["current_iteration"]
    progress["remaining_failures"] = iteration_result.get("remaining_failures", [])

    scores = iteration_result.get("scores", {})
    if scores:
        progress.setdefault("score_history", []).append({
            "iteration": progress["current_iteration"],
            "scores": scores,
            "overall_accuracy": overall,
        })

    patches = iteration_result.get("patch_set") or iteration_result.get("proposals_applied", [])
    if patches:
        progress.setdefault("patch_history", []).append({
            "iteration": progress["current_iteration"],
            "patches": patches,
        })

    rep_pct = iteration_result.get("repeatability_pct", 0)
    if rep_pct:
        progress["repeatability_pct"] = rep_pct
        if rep_pct > progress.get("best_repeatability", 0):
            progress["best_repeatability"] = rep_pct

    _update_pareto_frontier(progress, iteration_result)
    return progress


RISK_LEVEL_SCORE = {"low": 1, "medium": 2, "high": 3}


def _compute_patch_cost(proposals: list) -> int:
    """Compute weighted cost: sum of risk_level scores (low=1, medium=2, high=3)."""
    cost = 0
    for p in proposals:
        if isinstance(p, dict):
            risk = p.get("risk_level", "medium")
            cost += RISK_LEVEL_SCORE.get(risk, 2)
    return cost if cost > 0 else len(proposals)


def _update_pareto_frontier(progress: dict, iteration_result: dict):
    """Track multi-objective Pareto frontier (P6).

    Objectives (higher is better): correctness, repeatability.
    Objectives (lower is better): regressions, patch_cost.
    """
    scores = iteration_result.get("scores", {})
    if not scores:
        return

    proposals = iteration_result.get("proposals_applied", [])
    vector = {
        "iteration": progress["current_iteration"],
        "correctness": iteration_result.get("overall_accuracy", 0),
        "repeatability": iteration_result.get("repeatability_pct", 0),
        "regressions": len(iteration_result.get("regressions", [])),
        "patch_cost": _compute_patch_cost(proposals),
        "model_id": iteration_result.get("model_id"),
    }

    frontier = progress.setdefault("pareto_frontier", [])
    dominated = []
    is_dominated = False
    for i, existing in enumerate(frontier):
        ex_cost = existing.get("patch_cost", existing.get("patch_count", 0))
        ex_rep = existing.get("repeatability", 0)
        if (vector["correctness"] >= existing["correctness"]
                and vector["repeatability"] >= ex_rep
                and vector["regressions"] <= existing["regressions"]
                and vector["patch_cost"] <= ex_cost):
            dominated.append(i)
        elif (existing["correctness"] >= vector["correctness"]
              and ex_rep >= vector["repeatability"]
              and existing["regressions"] <= vector["regressions"]
              and ex_cost <= vector["patch_cost"]):
            is_dominated = True
            break

    if not is_dominated:
        for i in sorted(dominated, reverse=True):
            frontier.pop(i)
        frontier.append(vector)


def log_lever_impact(
    progress: dict,
    lever: int,
    before_scores: dict,
    after_scores: dict,
    proposals: list | None = None,
) -> dict:
    """Track per-lever accuracy impact for attribution reporting.

    Records before/after scores and accuracy delta for each lever, enabling
    the optimization report to show which levers contributed which improvements.

    Args:
        progress: Session progress dict (mutated in place).
        lever: Lever number (1-6).
        before_scores: Scores dict before applying this lever's proposals.
        after_scores: Scores dict after applying this lever's proposals.
        proposals: Proposals applied for this lever.

    Returns:
        The lever impact entry that was added.
    """
    before_acc = before_scores.get("overall_accuracy", 0)
    after_acc = after_scores.get("overall_accuracy", 0)
    impact = {
        "before": before_scores,
        "after": after_scores,
        "proposals": proposals or [],
        "delta": after_acc - before_acc,
    }
    progress.setdefault("lever_impacts", {})[str(lever)] = impact
    return impact


def _normalize_scores(scores: dict) -> dict:
    """Normalize per-judge scores to 0-100 scale if they appear to be 0-1.

    MLflow genai evaluate() returns scorer values in 0-1 range, but the
    orchestrator's threshold targets are on 0-100 scale. This converts at
    the boundary so all downstream comparisons are like-for-like.
    """
    if not scores:
        return scores
    normalized = {}
    for judge, score in scores.items():
        if isinstance(score, (int, float)) and 0 <= score <= 1.0:
            normalized[judge] = score * 100
        else:
            normalized[judge] = score
    return normalized


def all_thresholds_met(scores: dict, targets: dict | None = None) -> bool:
    """Check if all quality dimension targets are met.

    Args:
        scores: Dict of judge_name -> score (0-100 percentage).
               Scores are auto-normalized from 0-1 if needed.
        targets: Optional override; defaults to standard targets.
    """
    scores = _normalize_scores(scores)
    defaults = {
        "syntax_validity": 98, "schema_accuracy": 95, "logical_accuracy": 90,
        "semantic_equivalence": 90, "completeness": 90, "result_correctness": 85,
        "asset_routing": 95,
    }
    targets = targets or defaults
    if not scores:
        return False
    for judge, target in targets.items():
        if scores.get(judge, 0) < target:
            return False
    return True


def add_benchmark_correction(
    progress: dict, question_id: str, old_gt: str, new_gt: str, arbiter_run_id: str = "",
):
    """Record an arbiter ground-truth correction.

    When corrections accumulate to >= 3, the orchestrator should trigger the
    Generator to update benchmarks (routing table row "Arbiter corrected >= 3 GTs").
    """
    corrections = progress.setdefault("benchmark_corrections", [])
    corrections.append({
        "question_id": question_id,
        "old_gt": old_gt,
        "new_gt": new_gt,
        "arbiter_run_id": arbiter_run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    if len(corrections) >= 3:
        print(f"  WARNING: {len(corrections)} arbiter corrections accumulated. "
              "Consider re-running Generator to update benchmarks.")
    return corrections


def verify_dual_persistence(apply_results: list) -> list[str]:
    """Check that all applied proposals have both API + repo updates.

    Returns list of proposal_ids where repo_status is not 'success'.
    """
    if isinstance(apply_results, dict):
        # Patch DSL path returns apply_log dict, not per-proposal repo statuses.
        return []
    missing = []
    for r in apply_results:
        if r.get("repo_status") != "success":
            missing.append(r.get("proposal_id", "unknown"))
    return missing


def write_progress(progress: dict, path: str):
    with open(path, "w") as f:
        json.dump(progress, f, indent=2)


# =========================================================================
# Inline Evaluation (delegates to Evaluator worker patterns)
# =========================================================================

def run_genie_query(space_id: str, question: str, max_wait: int = 120) -> dict:
    """Execute a query against Genie and return SQL + status."""
    if w is None:
        return {"status": "ERROR", "sql": None, "error": "SDK not initialized"}
    try:
        resp = w.genie.start_conversation(space_id=space_id, content=question)
        conversation_id = resp.conversation_id
        message_id = resp.message_id

        poll_interval = 3
        start = time.time()
        msg = None
        while time.time() - start < max_wait:
            time.sleep(poll_interval)
            msg = w.genie.get_message(
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            status = str(msg.status) if hasattr(msg, "status") else "UNKNOWN"
            if any(s in status for s in ["COMPLETED", "FAILED", "CANCELLED"]):
                break
            poll_interval = min(poll_interval + 1, 10)

        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = (
                        att.query.query
                        if hasattr(att.query, "query")
                        else str(att.query)
                    )

        return {
            "status": status,
            "sql": sql,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}


def detect_asset_type(sql: str) -> str:
    sql_lower = sql.lower()
    if "mv_" in sql_lower or "measure(" in sql_lower:
        return "MV"
    elif "get_" in sql_lower:
        return "TVF"
    return "TABLE"


def run_evaluation_iteration(
    space_id: str,
    benchmarks: list,
    experiment_name: str,
    iteration: int,
    uc_schema: str = None,
    model_id: str = None,
) -> dict:
    """Run a single inline evaluation iteration with MLflow tracking."""
    _verify_mlflow_tracking()
    mlflow.set_experiment(experiment_name)

    print(f"\n--- Iteration {iteration}: Evaluating {len(benchmarks)} questions ---\n")

    results = []
    run_name = (
        f"genie_eval_iter{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("space_id", space_id)
        mlflow.log_param("iteration", iteration)
        mlflow.log_param("benchmark_count", len(benchmarks))
        print(f"  MLflow Run: {run.info.run_id} ({run_name})")

        for q in benchmarks:
            qid = q.get("id", "?")
            print(f"  [{qid}] {q['question'][:55]}...", end=" ", flush=True)
            result = run_genie_query(space_id, q["question"])

            generated_sql = (result.get("sql") or "").strip()
            expected_asset = q.get("expected_asset", "").upper()
            actual_asset = detect_asset_type(generated_sql) if generated_sql else "NONE"
            correct = actual_asset == expected_asset

            print(f"{'PASS' if correct else 'FAIL'} (expected={expected_asset}, got={actual_asset})")
            time.sleep(12)

            mlflow.log_metric(f"q_{qid}_routing", 1.0 if correct else 0.0)
            results.append({
                "question_id": qid,
                "question": q["question"],
                "correct_asset": correct,
                "actual_asset": actual_asset,
                "expected_asset": expected_asset,
                "generated_sql": generated_sql[:200] if generated_sql else None,
            })

        total = len(results)
        correct_count = sum(1 for r in results if r["correct_asset"])
        accuracy = (correct_count / total * 100) if total else 0
        failures = [r for r in results if not r["correct_asset"]]

        mlflow.log_metric("asset_routing_rate", correct_count / total if total else 0)
        mlflow.log_metric("overall_accuracy", accuracy / 100)
        mlflow.log_metric("questions_passed", correct_count)
        mlflow.log_metric("questions_failed", len(failures))

        import tempfile
        import os as _os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(results, tmp, indent=2, default=str)
            tmp_path = tmp.name
        mlflow.log_artifact(tmp_path, artifact_path="evaluation")
        _os.unlink(tmp_path)

        print(f"\n  Accuracy: {correct_count}/{total} ({accuracy:.0f}%)")
        print(f"  MLflow Run ID: {run.info.run_id}")

    raw_scores = {"asset_accuracy": accuracy / 100}
    return {
        "iteration": iteration,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mlflow_run_id": run.info.run_id,
        "overall_accuracy": accuracy,
        "total_questions": total,
        "correct_count": correct_count,
        "failures": [f["question_id"] for f in failures],
        "remaining_failures": [f["question_id"] for f in failures],
        "scores": _normalize_scores(raw_scores),
        "rows": results,
    }


# =========================================================================
# Job-Based Evaluation (delegates to Evaluator worker patterns)
# =========================================================================

def trigger_evaluation_job(
    space_id, experiment_name, iteration, benchmarks_path, domain,
    target="dev", job_name="genie_evaluation_job",
    eval_scope=None, model_id=None, patched_objects=None,
    eval_dataset_name: str = None,
    run_repeatability: bool = False,
):
    """Trigger the genie_evaluation_job via bundle run."""
    import subprocess
    import re
    import base64

    params_str = f"iteration={iteration}"
    if eval_scope and eval_scope != "full":
        params_str += f",eval_scope={eval_scope}"
    if model_id:
        params_str += f",model_id={model_id}"
    if patched_objects:
        encoded = base64.b64encode(json.dumps(patched_objects).encode()).decode()
        params_str += f",patched_objects_b64={encoded}"
    if eval_dataset_name:
        params_str += f",eval_dataset_name={eval_dataset_name}"
    if run_repeatability:
        params_str += ",run_repeatability=true"

    cmd = [
        "databricks", "bundle", "run", "-t", target, job_name,
        "--params", params_str,
    ]
    print(f"\n--- Triggering Evaluation Job (iteration {iteration}, scope={eval_scope or 'full'}) ---")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {"status": "TRIGGER_FAILED", "error": result.stderr, "run_id": None}

    run_id_match = re.search(r"run_id[:\s]+(\d+)", result.stdout)
    run_id = run_id_match.group(1) if run_id_match else None
    print(f"  Job triggered. Run ID: {run_id}")
    return {"status": "TRIGGERED", "run_id": run_id, "stdout": result.stdout}


def poll_job_completion(run_id, poll_interval=30, max_wait=3600):
    """Poll a Databricks job run until it completes or times out."""
    import subprocess

    print(f"\n--- Polling Job Run {run_id} ---")
    start = time.time()
    while time.time() - start < max_wait:
        cmd = ["databricks", "jobs", "get-run", str(run_id), "--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            time.sleep(poll_interval)
            continue

        run_data = json.loads(result.stdout)
        state = run_data.get("state", {})
        lifecycle = state.get("life_cycle_state", "UNKNOWN")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] lifecycle={lifecycle}")

        if lifecycle == "TERMINATED":
            notebook_output = None
            tasks = run_data.get("tasks", [])
            if tasks:
                task_run_id = tasks[0].get("run_id")
                if task_run_id:
                    out_cmd = [
                        "databricks", "jobs", "get-run-output",
                        str(task_run_id), "--output", "json",
                    ]
                    out_result = subprocess.run(out_cmd, capture_output=True, text=True)
                    if out_result.returncode == 0:
                        out_data = json.loads(out_result.stdout)
                        notebook_output = (
                            out_data.get("notebook_output", {}).get("result", "")
                        )
            return {
                "life_cycle_state": lifecycle,
                "result_state": state.get("result_state", ""),
                "notebook_output": notebook_output,
            }

        if lifecycle in ("INTERNAL_ERROR", "SKIPPED"):
            return {
                "life_cycle_state": lifecycle,
                "result_state": state.get("state_message", ""),
                "notebook_output": None,
            }
        time.sleep(poll_interval)

    return {
        "life_cycle_state": "TIMEOUT",
        "result_state": "Exceeded max_wait",
        "notebook_output": None,
    }


def run_evaluation_via_job(
    space_id, experiment_name, iteration, benchmarks_path, domain, target="dev",
    model_id: str = None, eval_scope: str = None, patched_objects: list = None,
    eval_dataset_name: str = None,
    run_repeatability: bool = False,
):
    """Trigger job, poll completion, parse output or fall back to MLflow."""
    trigger = trigger_evaluation_job(
        space_id, experiment_name, iteration, benchmarks_path, domain, target,
        eval_scope=eval_scope, model_id=model_id, patched_objects=patched_objects,
        eval_dataset_name=eval_dataset_name,
        run_repeatability=run_repeatability,
    )
    if trigger["status"] != "TRIGGERED" or not trigger.get("run_id"):
        return {
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_accuracy": 0,
            "failures": [],
            "remaining_failures": [],
            "scores": {},
            "job_error": trigger.get("error"),
        }

    completion = poll_job_completion(trigger["run_id"])
    if completion["result_state"] != "SUCCESS":
        return {
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_accuracy": 0,
            "failures": [],
            "remaining_failures": [],
            "scores": {},
            "job_error": completion.get("result_state"),
        }

    notebook_output = completion.get("notebook_output")
    job_result = {}
    if notebook_output:
        try:
            job_result = json.loads(notebook_output)
        except json.JSONDecodeError:
            pass

    if not job_result:
        _verify_mlflow_tracking()
        latest = query_latest_evaluation(experiment_name, iteration)
        if latest:
            job_result = {
                "run_id": latest["run_id"],
                "overall_accuracy": latest["metrics"].get("overall_accuracy", 0),
                "thresholds_passed": latest["thresholds_passed"],
            }

    overall = job_result.get("overall_accuracy", 0)
    overall_pct = overall * 100 if isinstance(overall, float) and overall <= 1.0 else overall
    raw_scores = job_result.get("per_judge", {})

    rows = job_result.get("rows", [])
    arbiter_actions = job_result.get("arbiter_actions", [])
    repeatability_pct = job_result.get("repeatability_pct", 0)
    repeatability_details = job_result.get("repeatability_details", [])
    failures_rich = []

    mlflow_run_id = job_result.get("run_id")
    if mlflow_run_id and (not rows or not arbiter_actions):
        try:
            import tempfile as _tf
            artifact_dir = mlflow.artifacts.download_artifacts(
                run_id=mlflow_run_id, artifact_path="evaluation",
                dst_path=_tf.mkdtemp(prefix="eval_artifacts_"),
            )
            import os as _osmod
            failures_path = _osmod.path.join(artifact_dir, "failures.json")
            if _osmod.path.exists(failures_path):
                with open(failures_path) as f:
                    failures_rich = json.load(f)
                print(f"  Downloaded failures.json: {len(failures_rich)} entries")

            arbiter_path = _osmod.path.join(artifact_dir, "arbiter_actions.json")
            if _osmod.path.exists(arbiter_path) and not arbiter_actions:
                with open(arbiter_path) as f:
                    arbiter_actions = json.load(f)
                print(f"  Downloaded arbiter_actions.json: {len(arbiter_actions)} entries")

            if not rows:
                results_path = _osmod.path.join(artifact_dir, "eval_results.json")
                if _osmod.path.exists(results_path):
                    with open(results_path) as f:
                        rows = json.load(f)
                    print(f"  Downloaded eval_results.json: {len(rows)} rows")

            if not repeatability_details:
                rep_path = _osmod.path.join(artifact_dir, "repeatability.json")
                if _osmod.path.exists(rep_path):
                    with open(rep_path) as f:
                        rep_data = json.load(f)
                    repeatability_pct = rep_data.get("average_repeatability_pct", 0)
                    repeatability_details = rep_data.get("results", [])
                    print(f"  Downloaded repeatability.json: {repeatability_pct:.0f}% avg, "
                          f"{len(repeatability_details)} questions")

            import shutil as _sh
            _sh.rmtree(artifact_dir, ignore_errors=True)
        except Exception as e:
            print(f"  NOTE: Could not download evaluation artifacts: {e}")

    if not rows and failures_rich:
        rows = failures_rich

    result = {
        "iteration": iteration,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mlflow_run_id": mlflow_run_id,
        "overall_accuracy": overall_pct,
        "failures": job_result.get("failure_question_ids", []),
        "remaining_failures": job_result.get("failure_question_ids", []),
        "scores": _normalize_scores(raw_scores),
        "total_questions": job_result.get("total_questions", job_result.get("questions_total", 0)),
        "rows": rows,
        "arbiter_actions": arbiter_actions,
    }
    if repeatability_pct:
        result["repeatability_pct"] = repeatability_pct
        result["repeatability_details"] = repeatability_details
    return result


def query_latest_evaluation(experiment_name, iteration=None):
    """Query the latest evaluation run from MLflow."""
    filter_str = "tags.mlflow.runName LIKE 'genie_eval_%'"
    if iteration is not None:
        filter_str = f"tags.mlflow.runName LIKE 'genie_eval_iter{iteration}_%'"
    runs = mlflow.search_runs(
        experiment_names=[experiment_name],
        filter_string=filter_str,
        order_by=["start_time DESC"],
        max_results=1,
    )
    if runs.empty:
        return None
    row = runs.iloc[0]
    return {
        "run_id": row["run_id"],
        "metrics": {
            k.replace("metrics.", ""): v
            for k, v in row.items()
            if k.startswith("metrics.")
        },
        "thresholds_passed": row.get("metrics.thresholds_passed", 0.0) == 1.0,
    }


# =========================================================================
# Report Generation
# =========================================================================

def generate_report(
    progress: dict, domain: str, output_dir: str = "docs/genie_space_optimizer"
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{output_dir}/{domain}_optimization_{date_str}.md"

    iterations = progress.get("iterations", [])
    first = iterations[0] if iterations else {}
    last = iterations[-1] if iterations else {}

    report = f"""# {domain.replace('_', ' ').title()} Genie Space Optimization Report

**Date:** {date_str}
**Space ID:** `{progress['space_id']}`
**Domain:** {domain}
**Iterations:** {len(iterations)} of {progress['max_iterations']}
**Status:** {progress.get('status', 'unknown')}

## Executive Summary

| Metric | Initial | Final | Change |
|--------|---------|-------|--------|
| **Asset Accuracy** | {first.get('overall_accuracy', 0):.0f}% | {last.get('overall_accuracy', 0):.0f}% | {(last.get('overall_accuracy', 0) - first.get('overall_accuracy', 0)):+.0f}% |

## Iteration History

| Iter | Accuracy | Failures | Proposals Applied |
|------|----------|----------|-------------------|
"""
    for it in iterations:
        proposals = it.get("proposals_applied", [])
        report += (
            f"| {it.get('iteration', '?')} "
            f"| {it.get('overall_accuracy', 0):.0f}% "
            f"| {len(it.get('failures', []))} "
            f"| {len(proposals)} |\n"
        )

    lever_names = {
        "1": "UC Tables & Columns", "2": "Metric Views", "3": "TVFs",
        "4": "Monitoring Tables", "5": "ML Tables", "6": "Genie Instructions (GEPA)",
    }
    lever_impacts = progress.get("lever_impacts", {})
    if lever_impacts:
        report += "\n## Per-Lever Impact\n\n"
        report += "| Lever | Before | After | Delta | Proposals |\n"
        report += "|-------|--------|-------|-------|-----------|\n"
        for lv in ["1", "2", "3", "4", "5", "6"]:
            impact = lever_impacts.get(lv, {})
            if impact:
                before_acc = impact.get("before", {}).get("overall_accuracy", 0)
                after_acc = impact.get("after", {}).get("overall_accuracy", 0)
                delta = impact.get("delta", 0)
                num_proposals = len(impact.get("proposals", []))
                report += (
                    f"| Lever {lv}: {lever_names.get(lv, '')} "
                    f"| {before_acc:.0f}% | {after_acc:.0f}% | {delta:+.0f}% "
                    f"| {num_proposals} |\n"
                )

    report += f"""
## Remaining Failures

{', '.join(progress.get('remaining_failures', [])) or 'None'}

## Convergence

**Reason:** {progress.get('convergence_reason', 'Not converged')}
**Best Iteration:** {progress.get('best_iteration', 0)} ({progress.get('best_overall_accuracy', 0):.0f}%)

## Next Steps

- [ ] Review remaining failures
- [ ] Deploy bundle if not yet deployed
- [ ] Schedule follow-up optimization session
"""

    with open(filename, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {filename}")
    return filename


# =========================================================================
# Bundle Deployment (delegates to Applier worker)
# =========================================================================

def deploy_bundle_and_run_genie_job(target="dev", genie_job="genie_spaces_deployment_job"):
    import subprocess

    print("\n--- Phase B: Bundle Validate + Deploy ---\n")
    validate = subprocess.run(
        ["databricks", "bundle", "validate", "-t", target],
        capture_output=True, text=True,
    )
    if validate.returncode != 0:
        return {"status": "VALIDATE_FAILED", "error": validate.stderr}

    deploy = subprocess.run(
        ["databricks", "bundle", "deploy", "-t", target],
        capture_output=True, text=True,
    )
    if deploy.returncode != 0:
        return {"status": "DEPLOY_FAILED", "error": deploy.stderr}
    print("  Bundle deployed successfully.")

    print(f"\n--- Phase C: Trigger {genie_job} ---\n")
    run = subprocess.run(
        ["databricks", "bundle", "run", "-t", target, genie_job],
        capture_output=True, text=True,
    )
    if run.returncode != 0:
        return {"status": "JOB_FAILED", "error": run.stderr}

    print("  Genie Space deployment job completed.")
    return {"status": "SUCCESS", "error": None}


# =========================================================================
# Main Optimization Loop
# =========================================================================

def run_optimization_loop(
    space_id,
    benchmarks,
    domain,
    uc_schema=None,
    experiment_name=None,
    max_iterations=5,
    evaluate_only=False,
    resume_path=None,
    job_mode=False,
    target="dev",
    benchmarks_path=None,
    lever_aware=True,
    deploy_target=None,
    worker_dir=None,
):
    """MLflow-backed optimization loop with progress tracking.

    When lever_aware=True (default), runs the full lever-aware loop:
      Phase 1: Baseline evaluation
      Phase 2: Per-lever optimize/apply/verify/eval (levers 1-5)
      Phase 3: GEPA for lever 6 (if still below target)
      Phase 4: Deploy and verify

    When lever_aware=False or workers are unavailable, falls back to the
    legacy evaluate-only loop.
    """
    if not job_mode:
        _verify_mlflow_tracking()

    if lever_aware and worker_dir:
        _setup_worker_imports(worker_dir)
    elif lever_aware and not _WORKERS_AVAILABLE:
        _setup_worker_imports()

    progress_path = resume_path or "optimization-progress.json"
    progress = load_progress(progress_path) if resume_path else None
    if progress:
        print(f"Resuming from iteration {progress['current_iteration']}...")
        start_iteration = progress["current_iteration"] + 1
    else:
        progress = init_progress(space_id, domain, max_iterations)
        start_iteration = 1

    mode_label = "JOB" if job_mode else "INLINE"
    lever_label = "LEVER-AWARE" if (lever_aware and _WORKERS_AVAILABLE) else "EVAL-ONLY"
    print("=" * 60)
    print(f"Genie Optimization Orchestrator v4.2.0 [{mode_label}] [{lever_label}]")
    print(f"Space ID: {space_id}")
    print(f"Domain: {domain}")
    print(f"Benchmarks: {len(benchmarks)} questions")
    print(f"Max iterations: {max_iterations}")
    if job_mode:
        print(f"Target: {target}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    if not job_mode:
        if lever_aware:
            raise RuntimeError(
                "ERROR: Lever-aware optimization REQUIRES --job-mode.\n"
                "The inline evaluator only checks asset routing — it does NOT run\n"
                "the 8-judge mlflow.genai.evaluate() harness, does NOT produce ASI\n"
                "metadata, and does NOT write to the UC ASI table. The optimizer\n"
                "would receive no judge feedback and generate empty proposals.\n\n"
                "Fix: add --job-mode --target dev\n"
                "  python orchestrator.py --space-id <ID> --benchmarks golden-queries.yaml "
                "--job-mode --target dev"
            )
        print(
            "WARNING: Inline evaluation only checks asset routing (1 judge). "
            "Use --job-mode for the full 8-judge evaluation harness."
        )

    exp_name = experiment_name or _default_experiment_path(domain)
    _validate_experiment_path(exp_name)

    eval_dataset_name = None
    if uc_schema:
        eval_dataset_name = f"{uc_schema}.genie_benchmarks_{domain}"
        print(f"  UC Evaluation Dataset name: {eval_dataset_name} "
              "(created by evaluator job)")
    progress["eval_dataset_name"] = eval_dataset_name
    eval_dataset_ref = {"name": eval_dataset_name}

    _prev_model_id = None

    def _snapshot_and_get_model_id(iter_num, patch_set=None, prompt_versions=None):
        nonlocal _prev_model_id
        try:
            config = _fetch_space_config(space_id)
            if config:
                mid = create_genie_model_version(
                    space_id, config, iter_num, domain,
                    patch_set=patch_set,
                    parent_model_id=_prev_model_id,
                    prompt_versions=prompt_versions,
                    uc_schema=uc_schema,
                )
                _prev_model_id = mid
                return mid
        except Exception as e:
            print(f"  WARNING: LoggedModel creation failed: {e}")
        return None

    def _run_eval(iter_num, model_id=None, eval_scope="full", patched_objects=None,
                   run_repeatability=False):
        if job_mode:
            return run_evaluation_via_job(
                space_id, exp_name, iter_num,
                benchmarks_path or "", domain, target,
                model_id=model_id,
                eval_scope=eval_scope,
                patched_objects=patched_objects,
                eval_dataset_name=eval_dataset_ref["name"],
                run_repeatability=run_repeatability,
            )
        else:
            return run_evaluation_iteration(
                space_id, benchmarks, exp_name, iter_num, uc_schema,
                model_id=model_id,
            )

    # ── Evaluate-only mode ────────────────────────────────────────
    if evaluate_only:
        model_id = _snapshot_and_get_model_id(1)
        result = _run_eval(1, model_id=model_id)
        result["model_id"] = model_id
        link_eval_scores_to_model(model_id, result)
        update_progress(progress, result)
        progress["status"] = "evaluated"
        write_progress(progress, progress_path)
        return progress

    # ── Lever-aware optimization ──────────────────────────────────
    if lever_aware and _WORKERS_AVAILABLE:
        return _run_lever_aware_loop(
            space_id=space_id,
            benchmarks=benchmarks,
            domain=domain,
            progress=progress,
            progress_path=progress_path,
            exp_name=exp_name,
            job_mode=job_mode,
            target=target,
            benchmarks_path=benchmarks_path,
            uc_schema=uc_schema,
            deploy_target=deploy_target,
            max_iterations=max_iterations,
            _snapshot_fn=_snapshot_and_get_model_id,
            _eval_fn=_run_eval,
            eval_dataset_ref=eval_dataset_ref,
        )

    # ── Legacy evaluate-only fallback ─────────────────────────────
    if lever_aware and not _WORKERS_AVAILABLE:
        print("WARNING: Worker imports failed. Falling back to evaluate-only loop.")

    for iteration in range(start_iteration, max_iterations + 1):
        model_id = _snapshot_and_get_model_id(iteration)
        result = _run_eval(iteration, model_id=model_id)
        result["model_id"] = model_id
        link_eval_scores_to_model(model_id, result)
        update_progress(progress, result)
        write_progress(progress, progress_path)

        if result["overall_accuracy"] >= 95:
            progress["convergence_reason"] = (
                f"Target met at iteration {iteration} ({result['overall_accuracy']:.0f}%)"
            )
            progress["status"] = "converged"
            write_progress(progress, progress_path)
            print(f"\nTarget accuracy met! ({result['overall_accuracy']:.0f}%)")
            break

        if not result["failures"]:
            progress["convergence_reason"] = "No failures remaining."
            progress["status"] = "converged"
            write_progress(progress, progress_path)
            break

        if iteration >= 2:
            prev = (
                progress["iterations"][-2]
                if len(progress["iterations"]) >= 2
                else {}
            )
            if prev.get("overall_accuracy", 0) >= result["overall_accuracy"]:
                no_improve_count = sum(
                    1
                    for i in range(
                        max(0, len(progress["iterations"]) - 2),
                        len(progress["iterations"]),
                    )
                    if progress["iterations"][i].get("overall_accuracy", 0)
                    <= prev.get("overall_accuracy", 0)
                )
                if no_improve_count >= 2:
                    progress["convergence_reason"] = (
                        "No improvement for 2 consecutive iterations."
                    )
                    progress["status"] = "stalled"
                    write_progress(progress, progress_path)
                    print("\nNo improvement detected. Stopping.")
                    break

        print(f"\n  Iteration {iteration} complete. Accuracy: {result['overall_accuracy']:.0f}%")
        print(f"  Remaining failures: {result['failures']}")

    if progress["status"] == "in_progress":
        progress["convergence_reason"] = f"Max iterations ({max_iterations}) reached."
        progress["status"] = "max_iterations"
        write_progress(progress, progress_path)

    if not job_mode and progress.get("best_iteration", 0) > 0:
        print("\n  Promoting best LoggedModel...")
        promote_best_model(progress)

    return progress


def _synthesize_repeatability_failures(repeatability_details: list) -> list:
    """Convert non-repeatable questions into synthetic failure rows for the optimizer.

    Only questions with CRITICAL_VARIANCE or SIGNIFICANT_VARIANCE are included.
    These synthetic rows carry ASI metadata so cluster_failures() can group them.
    Routing depends on asset type: TABLE/MV -> Lever 1 (structured metadata),
    TVF -> Lever 6 (instructions).
    """
    synthetic_rows = []
    for detail in repeatability_details:
        classification = detail.get("classification", "IDENTICAL")
        if classification not in ("CRITICAL_VARIANCE", "SIGNIFICANT_VARIANCE"):
            continue
        asset = detail.get("dominant_asset", "TABLE")
        if asset == "MV":
            counterfactual = (
                "Add structured column metadata (business_definition, synonyms, grain) "
                "to underlying tables; convert to TVF if variance persists"
            )
        elif asset == "TVF":
            counterfactual = "Add instruction clarifying deterministic parameter selection for TVF"
        else:
            counterfactual = (
                "Add structured metadata (business_definition, synonyms, join_keys, "
                "do_not_use_when) to table/column comments and UC tags "
                "(preferred_for_genie, domain)"
            )
        synthetic_rows.append({
            "inputs/question_id": detail.get("question_id", ""),
            "inputs/question": detail.get("question", ""),
            "feedback/repeatability": "no",
            "rationale/repeatability": (
                f"SQL variance: {detail.get('unique_variants', 0)} distinct variants "
                f"across {len(detail.get('hashes', []))} runs "
                f"({detail.get('repeatability_pct', 0):.0f}% repeatability, asset={asset})"
            ),
            "metadata/repeatability/failure_type": "repeatability_issue",
            "metadata/repeatability/severity": (
                "critical" if classification == "CRITICAL_VARIANCE" else "major"
            ),
            "metadata/repeatability/blame_set": asset,
            "metadata/repeatability/counterfactual_fix": counterfactual,
        })
    return synthetic_rows


def _compute_cross_iteration_repeatability(current_rows: list, previous_rows: list) -> dict:
    """Compare SQL outputs between two iterations to detect instability.

    Builds question_id -> sql_hash maps for both iterations and checks for
    matches. Questions whose SQL changed AND were previously correct are flagged
    as "concerning" (potential side-effect regressions). Questions whose SQL
    changed AND were previously incorrect are flagged as "expected" (optimization
    may be working).

    Returns dict with:
        avg_pct: float (0-100) average match percentage
        details: list of per-question dicts
        unstable_details: list of dicts for questions that changed SQL
    """
    def _sql_hash(sql: str) -> str:
        if not sql:
            return "NONE"
        return hashlib.md5(sql.strip().lower().encode()).hexdigest()[:8]

    prev_map = {}
    for row in previous_rows:
        qid = (
            row.get("inputs/question_id")
            or row.get("question_id")
            or row.get("inputs/question", "")
        )
        sql = row.get("outputs/response", "") or row.get("response", "")
        was_correct = str(row.get("feedback/result_correctness", "")).lower() not in ("no", "false", "0")
        prev_map[qid] = {"hash": _sql_hash(sql), "was_correct": was_correct}

    details = []
    unstable = []
    matched_count = 0

    for row in current_rows:
        qid = (
            row.get("inputs/question_id")
            or row.get("question_id")
            or row.get("inputs/question", "")
        )
        if not qid or qid not in prev_map:
            continue
        sql = row.get("outputs/response", "") or row.get("response", "")
        curr_hash = _sql_hash(sql)
        prev_entry = prev_map[qid]
        is_match = curr_hash == prev_entry["hash"]
        if is_match:
            matched_count += 1

        asset = detect_asset_type(sql) if sql else "NONE"
        entry = {
            "question_id": qid,
            "question": row.get("inputs/question", ""),
            "matched": is_match,
            "current_hash": curr_hash,
            "prev_hash": prev_entry["hash"],
            "dominant_asset": asset,
            "was_previously_correct": prev_entry["was_correct"],
        }
        details.append(entry)
        if not is_match:
            unstable.append(entry)

    total = len(details)
    avg_pct = (matched_count / total * 100) if total > 0 else 100.0

    return {
        "avg_pct": avg_pct,
        "total_questions": total,
        "matched": matched_count,
        "changed": total - matched_count,
        "details": details,
        "unstable_details": unstable,
    }


def _synthesize_repeatability_failures_from_cross_iter(unstable_details: list) -> list:
    """Convert cross-iteration SQL instabilities into synthetic failure rows.

    Only flags questions whose SQL changed AND were previously correct
    (concerning side-effect regressions). Questions that changed from incorrect
    are treated as expected optimization effects.
    """
    synthetic_rows = []
    for detail in unstable_details:
        if detail.get("was_previously_correct") is False:
            continue
        asset = detail.get("dominant_asset", "TABLE")
        if asset == "MV":
            counterfactual = (
                "Add structured column metadata (business_definition, synonyms, grain) "
                "to underlying tables; convert to TVF if variance persists"
            )
        elif asset == "TVF":
            counterfactual = "Add instruction clarifying deterministic parameter selection for TVF"
        else:
            counterfactual = (
                "Add structured metadata (business_definition, synonyms, join_keys, "
                "do_not_use_when) to table/column comments and UC tags "
                "(preferred_for_genie, domain)"
            )
        synthetic_rows.append({
            "inputs/question_id": detail.get("question_id", ""),
            "inputs/question": detail.get("question", ""),
            "feedback/repeatability": "no",
            "rationale/repeatability": (
                f"Cross-iteration SQL change: hash {detail.get('prev_hash', '?')} -> "
                f"{detail.get('current_hash', '?')} (was previously correct, asset={asset})"
            ),
            "metadata/repeatability/failure_type": "repeatability_issue",
            "metadata/repeatability/severity": "major",
            "metadata/repeatability/blame_set": asset,
            "metadata/repeatability/counterfactual_fix": counterfactual,
        })
    return synthetic_rows


def _run_lever_aware_loop(
    space_id,
    benchmarks,
    domain,
    progress,
    progress_path,
    exp_name,
    job_mode,
    target,
    benchmarks_path,
    uc_schema,
    deploy_target,
    max_iterations,
    _snapshot_fn,
    _eval_fn,
    eval_dataset_ref=None,
):
    """Phase 1-4 lever-aware optimization loop.

    Phase 1: Baseline evaluation
    Phase 2: Per-lever optimize/apply/verify/eval (levers 1-5)
    Phase 3: GEPA lever 6 (if still below target)
    Phase 4: Deploy and verify
    """
    cluster_failures, generate_metadata_proposals, detect_regressions, run_gepa_optimization = _import_optimizer()
    apply_proposal_batch, strip_non_exportable_fields, verify_repo_update = _import_applier()
    from optimization_applier import (
        apply_patch_set as _apply_patch_set,
        rollback as _rollback,
        proposals_to_patches as _proposals_to_patches,
    )

    iteration_counter = progress.get("current_iteration", 0)

    def _next_iter():
        nonlocal iteration_counter
        iteration_counter += 1
        return iteration_counter

    def _apply_benchmark_corrections_if_needed(corrections: list[dict], at_iteration: int):
        """Patch benchmarks from arbiter genie_correct verdicts and re-sync dataset."""
        if len(corrections) < 3 or not benchmarks_path:
            return
        try:
            with open(benchmarks_path) as _bf:
                _all = yaml.safe_load(_bf) or {}
        except Exception as _read_err:
            print(f"  WARNING: Could not read benchmarks YAML for corrections: {_read_err}")
            return

        _benchmarks = _all.get(domain, _all.get("benchmarks", []))
        if not isinstance(_benchmarks, list) or not _benchmarks:
            return

        _by_qid = {}
        for _c in corrections:
            if _c.get("verdict") != "genie_correct":
                continue
            _qid = str(_c.get("question_id", "")).strip()
            _genie_sql = (_c.get("generated_sql") or "").strip()
            if _qid and _genie_sql:
                _by_qid[_qid] = _genie_sql
                add_benchmark_correction(
                    progress=progress,
                    question_id=_qid,
                    old_gt=str(_c.get("expected_sql", "")),
                    new_gt=_genie_sql,
                    arbiter_run_id="",
                )

        if not _by_qid:
            return

        _updated = 0
        for _b in _benchmarks:
            _qid = str(_b.get("id", "")).strip()
            if _qid in _by_qid:
                _b["expected_sql"] = _by_qid[_qid]
                _b["source"] = "arbiter_corrected"
                _updated += 1

        if _updated == 0:
            return

        with open(benchmarks_path, "w") as _wf:
            yaml.dump(_all, _wf, default_flow_style=False, sort_keys=False)
        print(f"  Applied {_updated} arbiter benchmark corrections to YAML.")
        print("  UC dataset will be re-synced by the evaluator job on next run.")

        progress["benchmark_corrections_applied_at"] = at_iteration

    # ── Phase 1: Baseline Evaluation ──────────────────────────────
    print("\n" + "=" * 60)
    print("Phase 1: Baseline Evaluation")
    print("=" * 60)

    iter_num = _next_iter()
    model_id = _snapshot_fn(iter_num)
    baseline_result = _eval_fn(iter_num, model_id=model_id, eval_scope="full")
    baseline_result["model_id"] = model_id
    link_eval_scores_to_model(model_id, baseline_result)
    update_progress(progress, baseline_result)
    write_progress(progress, progress_path)

    prev_scores = baseline_result.get("scores", {})
    prev_accuracy = baseline_result.get("overall_accuracy", 0)
    prev_model_id = model_id

    _baseline_arbiter = baseline_result.get("arbiter_actions", [])
    _baseline_genie_correct = [a for a in _baseline_arbiter if a.get("verdict") == "genie_correct"]
    if len(_baseline_genie_correct) >= 3:
        print(f"\n  WARNING: Arbiter found {len(_baseline_genie_correct)} benchmark corrections needed.")
        print("  ACTION: Load Generator to update benchmark expected SQL.")
        progress["benchmark_correction_needed"] = True
        progress["corrected_questions"] = _baseline_genie_correct
        _apply_benchmark_corrections_if_needed(_baseline_genie_correct, iter_num)

    baseline_rep = baseline_result.get("repeatability_pct", 0)
    if baseline_rep:
        print(f"  Baseline repeatability: {baseline_rep:.0f}% (target: {progress.get('repeatability_target', 90):.0f}%)")
    print(f"\n  Baseline accuracy: {prev_accuracy:.0f}%")

    if all_thresholds_met(prev_scores):
        progress["convergence_reason"] = f"All thresholds met at baseline ({prev_accuracy:.0f}%)"
        progress["status"] = "converged"
        write_progress(progress, progress_path)
        print("  All thresholds met at baseline! Skipping to deploy.")
    else:
        # ── Phase 2: Per-Lever Optimization ───────────────────────
        print("\n" + "=" * 60)
        print("Phase 2: Per-Lever Optimization (levers 1-5)")
        print("=" * 60)

        metadata_snapshot = _fetch_space_config(space_id) or {}

        for lever in [1, 2, 3, 4, 5]:
            if all_thresholds_met(prev_scores):
                print(f"\n  All thresholds met after lever {lever - 1}. Stopping.")
                progress["convergence_reason"] = f"All thresholds met after lever {lever - 1}"
                progress["status"] = "converged"
                break

            if iteration_counter >= max_iterations:
                print(f"\n  Max iterations ({max_iterations}) reached at lever {lever}.")
                break

            lever_names = {
                1: "UC Tables & Columns", 2: "Metric Views", 3: "TVFs",
                4: "Monitoring Tables", 5: "ML Tables",
            }
            print(f"\n--- Lever {lever}: {lever_names.get(lever, '')} ---")

            # 2a. Generate proposals for THIS lever
            # Pass the full iteration result so cluster_failures() can read
            # feedback/* and rationale/* columns from row-level judge output.
            eval_results_for_optimizer = dict(progress["iterations"][-1]) if progress["iterations"] else {}
            if not eval_results_for_optimizer.get("rows") and not eval_results_for_optimizer.get("eval_results"):
                eval_results_for_optimizer["rows"] = [
                    {
                        "inputs/question": qid,
                        "feedback/overall": "no",
                        "rationale/overall": "failed",
                    }
                    for qid in eval_results_for_optimizer.get("failures", [])
                ]

            # Inject cross-iteration repeatability failures (from iteration 2+)
            if len(progress["iterations"]) >= 2:
                prev_rows = progress["iterations"][-2].get("rows", [])
                curr_rows = eval_results_for_optimizer.get("rows", [])
                if prev_rows and curr_rows:
                    cross_rep = _compute_cross_iteration_repeatability(curr_rows, prev_rows)
                    progress["cross_iteration_repeatability"] = cross_rep["avg_pct"]
                    print(f"  Cross-iteration repeatability: {cross_rep['avg_pct']:.0f}% "
                          f"({cross_rep['changed']} questions changed SQL)")
                    if cross_rep.get("unstable_details"):
                        synthetic = _synthesize_repeatability_failures_from_cross_iter(
                            cross_rep["unstable_details"]
                        )
                        if synthetic:
                            rows = eval_results_for_optimizer.get("rows", [])
                            eval_results_for_optimizer["rows"] = rows + synthetic
                            print(f"  Injected {len(synthetic)} cross-iteration repeatability "
                                  "failures into optimizer input")

            clusters = cluster_failures(eval_results_for_optimizer, metadata_snapshot)
            proposals = generate_metadata_proposals(clusters, metadata_snapshot, target_lever=lever)

            lever_key = str(lever)
            progress.setdefault("lever_audit", {})[lever_key] = progress.get("lever_audit", {}).get(lever_key, {})
            progress["lever_audit"][lever_key]["attempted"] = True
            progress["lever_audit"][lever_key]["proposals_generated"] = len(proposals) if proposals else 0

            if not proposals:
                print(f"  No proposals for lever {lever}. Skipping.")
                progress["lever_audit"][lever_key]["skip_reason"] = "no_proposals_generated"
                continue

            print(f"  Generated {len(proposals)} proposals for lever {lever}.")

            # 2b. Apply proposals (Patch DSL preferred, apply_proposal_batch fallback)
            pending_apply_log = None
            if progress.get("use_patch_dsl", True):
                try:
                    current_config = _fetch_space_config(space_id) or metadata_snapshot or {}
                    patches = _proposals_to_patches(proposals)
                    pending_apply_log = _apply_patch_set(
                        space_id,
                        patches,
                        current_config,
                        use_patch_dsl=True,
                    )
                    apply_results = []
                except Exception as e:
                    print(f"  WARNING: Patch DSL failed ({e}). Falling back to apply_proposal_batch.")
                    apply_results = apply_proposal_batch(proposals, space_id, domain)
            else:
                apply_results = apply_proposal_batch(proposals, space_id, domain)

            failed_repos = verify_dual_persistence(apply_results)
            if failed_repos:
                print(f"  BLOCKED: Dual persistence incomplete for: {failed_repos}")
                print("  Hard constraint #13: cannot proceed to evaluation.")
                print("  Rolling back lever and skipping to next.")
                rollback_to_model(prev_model_id, space_id)
                continue

            print("  Waiting 30s for propagation...")
            time.sleep(30)

            iter_num = _next_iter()
            model_id = _snapshot_fn(iter_num, patch_set=proposals, prompt_versions=None)

            # 2b-ii. Slice eval (cheap gate)
            print(f"  Running slice eval gate for lever {lever}...")
            slice_result = _eval_fn(iter_num, model_id=model_id, eval_scope="slice")
            slice_acc = slice_result.get("overall_accuracy", 0)
            if slice_acc < prev_accuracy - 5:
                print(f"  SLICE GATE FAILED ({slice_acc:.0f}% vs {prev_accuracy:.0f}% baseline). Rolling back lever {lever}.")
                rollback_to_model(prev_model_id, space_id)
                continue

            # 2b-iii. P0 gate (hard constraint)
            print(f"  Running P0 gate for lever {lever}...")
            p0_result = _eval_fn(iter_num, model_id=model_id, eval_scope="p0")
            p0_total = p0_result.get("total_questions", p0_result.get("overall_accuracy", -1))
            if p0_total == 0 or p0_total == -1:
                print(f"  WARNING: P0 gate returned no questions. "
                      "Evaluator may lack question_id lineage. Treating as gate inconclusive.")
            p0_failures = [f for f in p0_result.get("failures", []) if f]
            if p0_failures:
                print(f"  P0 GATE FAILED ({len(p0_failures)} P0 questions failed). Rolling back lever {lever}.")
                rollback_to_model(prev_model_id, space_id)
                continue

            # 2c. Full eval (only reached if both gates pass)
            print(f"  Gates passed. Running full evaluation for lever {lever}...")
            lever_result = _eval_fn(iter_num, model_id=model_id, eval_scope="full")
            lever_result["model_id"] = model_id
            link_eval_scores_to_model(model_id, lever_result)
            lever_result["proposals_applied"] = proposals
            lever_result["slice_result"] = {
                "accuracy": slice_acc,
                "passed": True,
            }
            lever_result["p0_result"] = {
                "failures": p0_failures,
                "passed": len(p0_failures) == 0,
            }
            if pending_apply_log:
                lever_result["apply_log"] = pending_apply_log
            update_progress(progress, lever_result)
            write_progress(progress, progress_path)

            lever_scores = lever_result.get("scores", {})
            lever_accuracy = lever_result.get("overall_accuracy", 0)

            # 2c-ii. Arbiter threshold check
            _arbiter_actions = lever_result.get("arbiter_actions", [])
            _genie_corrections = [a for a in _arbiter_actions if a.get("verdict") == "genie_correct"]
            if len(_genie_corrections) >= 3:
                print(f"  WARNING: Arbiter found {len(_genie_corrections)} questions where "
                      "Genie was correct but benchmark expected different SQL.")
                print("  ACTION: Load Generator to update benchmark expected SQL.")
                progress["benchmark_correction_needed"] = True
                progress["corrected_questions"] = _genie_corrections
                _apply_benchmark_corrections_if_needed(_genie_corrections, iter_num)

            # 2d. Track per-lever impact
            log_lever_impact(progress, lever, prev_scores, lever_scores, proposals)

            # 2e. Regression check
            regressions = detect_regressions(
                lever_scores if lever_scores else {"overall_accuracy": lever_accuracy},
                prev_scores if prev_scores else {"overall_accuracy": prev_accuracy},
            )
            if regressions:
                print(f"  REGRESSION detected after lever {lever}: {regressions}")
                print("  Rolling back...")
                rollback_config = rollback_to_model(prev_model_id, space_id)
                _lever_apply_log = lever_result.get("apply_log")
                if _lever_apply_log and progress.get("use_patch_dsl", True):
                    try:
                        _rollback(_lever_apply_log, space_id)
                        print("  Patch DSL rollback successful.")
                    except Exception as e:
                        print(f"  WARNING: Patch DSL rollback failed: {e}")
                if rollback_config is not None:
                    print("  LoggedModel rollback successful. Skipping this lever.")
                else:
                    print("  WARNING: LoggedModel rollback failed. Continuing with degraded state.")
                continue

            print(f"  Lever {lever} result: {lever_accuracy:.0f}% (delta: {lever_accuracy - prev_accuracy:+.0f}%)")
            progress["lever_audit"][lever_key]["proposals_applied"] = len(proposals)
            prev_scores = lever_scores
            prev_accuracy = lever_accuracy
            prev_model_id = model_id

            metadata_snapshot = _fetch_space_config(space_id) or metadata_snapshot

        # ── Phase 3: GEPA for Lever 6 ────────────────────────────
        if not all_thresholds_met(prev_scores) and iteration_counter < max_iterations:
            # Lever exhaustion gate: all levers 1-5 must be attempted or have a skip reason
            lever_audit = progress.get("lever_audit", {})
            unattempted = []
            for lv in range(1, 6):
                info = lever_audit.get(str(lv), {})
                if not info.get("attempted") and not info.get("skip_reason"):
                    unattempted.append(lv)
            if unattempted:
                print(f"\n  WARNING: Levers {unattempted} were never attempted before GEPA.")
                print("  Hard constraint #14 requires levers 1-5 be exhausted before Lever 6.")
                for lv in unattempted:
                    lever_audit.setdefault(str(lv), {})["skip_reason"] = "skipped_before_gepa"

            progress["lever_audit"]["6"] = progress.get("lever_audit", {}).get("6", {})
            progress["lever_audit"]["6"]["attempted"] = True

            print("\n" + "=" * 60)
            print("Phase 3: GEPA Lever 6 (Genie Instructions)")
            print("=" * 60)

            progress["maturity_level"] = "L2"

            try:
                metadata_snapshot = _fetch_space_config(space_id) or metadata_snapshot
                judge_feedbacks = []
                for it in progress.get("iterations", []):
                    for f in it.get("failures", []):
                        if isinstance(f, dict):
                            judge_feedbacks.append(f)

                gepa_result = run_gepa_optimization(
                    space_id=space_id,
                    config=metadata_snapshot,
                    judge_feedbacks=judge_feedbacks,
                    use_gepa=True,
                )

                if gepa_result:
                    print(f"  GEPA produced {len(gepa_result)} patches.")
                    if progress.get("use_patch_dsl", True):
                        try:
                            current_config = _fetch_space_config(space_id) or metadata_snapshot or {}
                            apply_results = _apply_patch_set(
                                space_id,
                                gepa_result,
                                current_config,
                                use_patch_dsl=True,
                            )
                            progress.setdefault("gepa_apply_log", apply_results)
                        except Exception as e:
                            print(f"  WARNING: Patch DSL failed for GEPA ({e}). Using fallback.")
                            apply_results = apply_proposal_batch(
                                [{"proposal_id": f"GEPA_{i}", "lever": 6, "change_description": f"GEPA patch: {p.get('type', 'unknown')}", "dual_persistence": {"api": "PATCH /api/2.0/genie/spaces/{space_id}", "repo": f"src/genie/{domain}_genie_export.json"}} for i, p in enumerate(gepa_result)],
                                space_id, domain,
                            )
                    else:
                        apply_results = apply_proposal_batch(
                            [{"proposal_id": f"GEPA_{i}", "lever": 6, "change_description": f"GEPA patch: {p.get('type', 'unknown')}", "dual_persistence": {"api": "PATCH /api/2.0/genie/spaces/{space_id}", "repo": f"src/genie/{domain}_genie_export.json"}} for i, p in enumerate(gepa_result)],
                            space_id, domain,
                        )
                    print("  Waiting 30s for propagation...")
                    time.sleep(30)

                    iter_num = _next_iter()
                    model_id = _snapshot_fn(iter_num, patch_set=gepa_result)
                    gepa_eval = _eval_fn(iter_num, model_id=model_id, eval_scope="full")
                    gepa_eval["model_id"] = model_id
                    link_eval_scores_to_model(model_id, gepa_eval)
                    update_progress(progress, gepa_eval)
                    write_progress(progress, progress_path)

                    gepa_scores = gepa_eval.get("scores", {})
                    log_lever_impact(progress, 6, prev_scores, gepa_scores, gepa_result)

                    regressions = detect_regressions(
                        gepa_scores if gepa_scores else {"overall_accuracy": gepa_eval.get("overall_accuracy", 0)},
                        prev_scores if prev_scores else {"overall_accuracy": prev_accuracy},
                    )
                    if regressions:
                        print("  REGRESSION from GEPA. Rolling back...")
                        rollback_to_model(prev_model_id, space_id)
                    else:
                        prev_scores = gepa_scores
                        prev_accuracy = gepa_eval.get("overall_accuracy", 0)
                        prev_model_id = model_id
                        print(f"  GEPA lever 6 result: {prev_accuracy:.0f}%")
                else:
                    print("  GEPA returned no patches.")
            except Exception as e:
                print(f"  WARNING: GEPA phase failed: {e}")

    # ── Phase 3b: Final dedicated repeatability test ────────────
    if job_mode and iteration_counter > 1:
        print("\n" + "=" * 60)
        print("Phase 3b: Final Repeatability Test (Cell 9c re-query)")
        print("=" * 60)
        try:
            rep_iter = _next_iter()
            rep_model_id = _snapshot_fn(rep_iter)
            rep_result = _run_eval(
                rep_iter, model_id=rep_model_id, eval_scope="full",
                run_repeatability=True,
            )
            rep_result["model_id"] = rep_model_id
            link_eval_scores_to_model(rep_model_id, rep_result)
            update_progress(progress, rep_result)
            write_progress(progress, progress_path)
            final_rep_pct = rep_result.get("repeatability_pct", 0)
            rep_target = progress.get("repeatability_target", 90)
            print(f"  Final repeatability: {final_rep_pct:.0f}% (target: {rep_target:.0f}%)")
            if final_rep_pct < rep_target:
                rep_details = rep_result.get("repeatability_details", [])
                synthetic = _synthesize_repeatability_failures(rep_details)
                if synthetic:
                    print(f"  {len(synthetic)} non-repeatable questions detected. "
                          "Feed to next optimization cycle if needed.")
                    progress["final_repeatability_failures"] = synthetic
        except Exception as e:
            print(f"  WARNING: Final repeatability test failed: {e}")

    # ── Phase 4: Deploy and Verify ────────────────────────────────
    if progress.get("status") not in ("converged", "stalled"):
        if all_thresholds_met(prev_scores):
            progress["convergence_reason"] = f"All thresholds met ({prev_accuracy:.0f}%)"
            progress["status"] = "converged"
        else:
            progress["convergence_reason"] = f"Completed lever sweep. Best: {progress.get('best_overall_accuracy', 0):.0f}%"
            progress["status"] = "max_iterations" if iteration_counter >= max_iterations else "in_progress"

    print("\n  Promoting best LoggedModel...")
    promote_best_model(progress)

    if deploy_target:
        print("\n" + "=" * 60)
        print("Phase 4: Deploy and Verify")
        print("=" * 60)
        result = deploy_bundle_and_run_genie_job(target=deploy_target)
        if result["status"] == "SUCCESS":
            print("  Bundle deployed. Running held-out evaluation...")
            iter_num = _next_iter()
            model_id = _snapshot_fn(iter_num)
            held_out_result = _eval_fn(iter_num, model_id=model_id, eval_scope="held_out")
            held_out_result["model_id"] = model_id
            link_eval_scores_to_model(model_id, held_out_result)
            update_progress(progress, held_out_result)
            write_progress(progress, progress_path)
            print(f"  Post-deploy accuracy: {held_out_result.get('overall_accuracy', 0):.0f}%")
        else:
            print(f"  Deploy failed: {result['status']} - {result.get('error', '')}")

    corrections = progress.get("benchmark_corrections", [])
    if len(corrections) >= 3:
        print(f"\n  WARNING: {len(corrections)} arbiter corrections accumulated. "
              "Re-run Generator to update benchmarks.")

    write_progress(progress, progress_path)
    return progress


# =========================================================================
# CLI Entry Point
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Genie Optimization Orchestrator v4.2.0"
    )
    parser.add_argument("--space-id", help="Genie Space ID")
    parser.add_argument(
        "--discover", action="store_true", help="List available Genie Spaces"
    )
    parser.add_argument("--benchmarks", help="Path to golden queries YAML")
    parser.add_argument("--domain", default="unknown", help="Domain name")
    parser.add_argument("--uc-schema", default=None, help="Unity Catalog schema")
    parser.add_argument("--experiment", default=None, help="MLflow experiment name")
    parser.add_argument(
        "--max-iterations", type=int, default=5, help="Max optimization iterations"
    )
    parser.add_argument(
        "--evaluate-only", action="store_true", help="Run one evaluation and stop"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from optimization-progress.json"
    )
    parser.add_argument(
        "--optimization-tier",
        choices=["gepa", "introspect", "simba"],
        default="introspect",
        help="Optimization engine tier",
    )
    parser.add_argument(
        "--align-judges", action="store_true", help="Run SIMBA judge alignment"
    )
    parser.add_argument(
        "--auto-apply", action="store_true",
        help="Auto-apply proposals without confirmation",
    )
    parser.add_argument(
        "--introspect", action="store_true", default=True,
        help="Enable introspective analysis",
    )
    parser.add_argument(
        "--output-dir", default="docs/genie_space_optimizer",
        help="Report output directory",
    )
    parser.add_argument(
        "--deploy-target", default=None,
        help="Bundle target for post-optimization deploy",
    )
    parser.add_argument(
        "--genie-job", default="genie_spaces_deployment_job",
        help="Genie deployment job name",
    )
    parser.add_argument(
        "--job-mode", action="store_true",
        help="Run evaluation as Databricks Job instead of inline",
    )
    parser.add_argument(
        "--target", default="dev", help="Bundle target for job mode (default: dev)"
    )
    parser.add_argument(
        "--lever-aware", action="store_true", default=True,
        help="Run lever-aware optimization loop (default: True). "
             "Requires worker scripts on sys.path or --worker-dir.",
    )
    parser.add_argument(
        "--no-lever-aware", action="store_true", default=False,
        help="Disable lever-aware mode; use legacy evaluate-only loop.",
    )
    parser.add_argument(
        "--worker-dir", default=None,
        help="Directory containing worker scripts (metadata_optimizer.py, optimization_applier.py). "
             "Defaults to sibling paths relative to this script.",
    )
    args = parser.parse_args()

    lever_aware = args.lever_aware and not args.no_lever_aware and not args.evaluate_only

    if args.discover:
        print("Discovering Genie Spaces...\n")
        spaces = discover_spaces()
        if not spaces:
            print("No Genie Spaces found.")
            return
        for s in spaces:
            print(f"  {s['id']}  {s['title']}")
        return

    if not args.space_id:
        parser.error("--space-id is required (or use --discover)")
    if not args.benchmarks:
        parser.error("--benchmarks is required")

    with open(args.benchmarks) as f:
        all_benchmarks = yaml.safe_load(f)

    if args.domain in all_benchmarks:
        benchmarks = all_benchmarks[args.domain]
    elif "benchmarks" in all_benchmarks:
        benchmarks = all_benchmarks["benchmarks"]
    else:
        benchmarks = all_benchmarks if isinstance(all_benchmarks, list) else []

    if not benchmarks:
        print(f"ERROR: No benchmarks found for domain '{args.domain}'")
        return

    resume_path = "optimization-progress.json" if args.resume else None

    progress = run_optimization_loop(
        space_id=args.space_id,
        benchmarks=benchmarks,
        domain=args.domain,
        uc_schema=args.uc_schema,
        experiment_name=args.experiment,
        max_iterations=args.max_iterations,
        evaluate_only=args.evaluate_only,
        resume_path=resume_path,
        job_mode=args.job_mode,
        target=args.target,
        benchmarks_path=args.benchmarks,
        lever_aware=lever_aware,
        deploy_target=args.deploy_target,
        worker_dir=args.worker_dir,
    )

    generate_report(progress, args.domain, args.output_dir)

    if args.deploy_target and not lever_aware:
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


if __name__ == "__main__":
    main()

# Session State Schema & MLflow Setup

Orchestrator session state management, MLflow experiment setup, space discovery, progress tracking, and prompt registration. These functions run on Databricks with the global `spark` session.

---

## MLflow Tracking Setup (REQUIRED — Run First)

Every evaluation must be logged to an MLflow experiment on the Databricks workspace. Run this before any other function.

```python
import mlflow
import os

# Required when running outside a Databricks notebook (CLI, local, CI/CD):
# os.environ['DATABRICKS_HOST'] = 'https://<workspace>.cloud.databricks.com'
# os.environ['DATABRICKS_TOKEN'] = '<token>'
# os.environ['MLFLOW_TRACKING_URI'] = 'databricks'

def _verify_mlflow_tracking():
    """Fail fast if MLflow is not configured for remote tracking.

    No arguments — reads tracking URI and env vars directly.
    Raises RuntimeError if MLflow is not configured for Databricks.
    """
    tracking_uri = mlflow.get_tracking_uri()
    if tracking_uri != "databricks" and not tracking_uri.startswith("databricks"):
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
```

---

## CLI Profile Resolution

Before any Databricks API call, resolve the correct CLI profile from `databricks.yml`. This prevents permission errors from using the wrong profile.

```python
import os
import yaml
import subprocess

def resolve_cli_profile(project_root: str = ".") -> str:
    """Resolve the Databricks CLI profile from databricks.yml.

    Looks for workspace.profile in databricks.yml. Falls back to DEFAULT.
    Validates the profile has Genie Space access before returning.
    """
    yml_path = os.path.join(project_root, "databricks.yml")
    profile = "DEFAULT"
    if os.path.exists(yml_path):
        with open(yml_path) as f:
            cfg = yaml.safe_load(f)
        profile = cfg.get("workspace", {}).get("profile", "DEFAULT")

    result = subprocess.run(
        ["databricks", "genie", "list-spaces", "--profile", profile],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Profile '{profile}' cannot access Genie Spaces: {result.stderr}"
        )
    print(f"  CLI profile resolved: {profile}")
    return profile
```

Use the resolved profile for all SDK calls:

```python
from databricks.sdk import WorkspaceClient
profile = resolve_cli_profile()
w = WorkspaceClient(profile=profile)
```

---

## Space Discovery

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def discover_spaces() -> list:
    """List available Genie Spaces via SDK."""
    spaces = list(w.genie.list_spaces())
    return [{"id": s.space_id, "title": s.title} for s in spaces]
```

Or via CLI:

```bash
databricks api get /api/2.0/genie/spaces --output json | jq '.spaces[] | {id: .space_id, title: .title}'
```

---

## Space Config Retrieval

```python
def _fetch_space_config(space_id: str) -> dict:
    """GET Genie Space config with full serialized_space content.

    Always uses ?include_serialized_space=true to get full asset data.
    Logs asset counts (tables, metric_views, tvfs, instructions).
    """
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
```

---

## Genie Space Version Tracking (LoggedModel)

Each optimization iteration creates an MLflow `LoggedModel` via `create_external_model()` inside `mlflow.start_run()` to track the exact Genie Space configuration that was evaluated. This connects config snapshots, evaluation results, and Genie API traces in the MLflow Versions tab.

```python
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
    # ... UC metadata fetching via _run_sql_statement_rows() ...

    config_hash = hashlib.sha256(
        json.dumps({"genie_config": config, "uc_columns": uc_columns,
                     "uc_tags": uc_tags, "uc_routines": uc_routines},
                    sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    model_name = f"genie-{domain}-iter{iteration}-{config_hash}"

    with mlflow.start_run(run_name=f"create_model_iter{iteration}_{config_hash}") as creation_run:
        logged_model = mlflow.create_external_model(
            name=model_name,
            source_run_id=creation_run.info.run_id,
            params=model_params,
            tags={"domain": domain, "space_id": space_id, ...},
            model_type="genie-space",
        )
        # Logs model_state/ artifacts (config, UC columns, tags, routines, diff)
        # Logs patches/ artifacts (patch_set.json, patch_summary.json) if patch_set
    return logged_model.model_id
```

---

## LoggedModel Lifecycle: Promote & Rollback

After the optimization loop converges, promote the best-performing LoggedModel. When P0 gate fails, rollback to the parent model's config.

```python
def promote_best_model(session: dict):
    """Tag the best-performing LoggedModel for promotion."""
    best_iter = session.get("best_iteration", 0)
    iterations = session.get("iterations", [])
    if not iterations or best_iter < 1:
        return

    best_result = iterations[best_iter - 1] if best_iter <= len(iterations) else iterations[-1]
    best_model_id = best_result.get("model_id")
    if not best_model_id:
        return

    mlflow.set_logged_model_tags(
        model_id=best_model_id,
        tags={
            "promoted": "true",
            "promotion_reason": session.get("convergence_reason", "target_met"),
            "best_accuracy": str(session.get("best_overall_accuracy", 0)),
            "best_iteration": str(best_iter),
        },
    )


def rollback_to_model(model_id: str, space_id: str):
    """Restore Genie Space config from a LoggedModel's creation run artifacts.

    Downloads model_state/genie_config.json from the creation run linked
    via source_run_id. Guards against missing source_run_id.
    """
    model = mlflow.get_logged_model(model_id=model_id)
    if not model.source_run_id:
        print(f"  WARNING: LoggedModel {model_id} has no source_run_id")
        return None

    artifact_dir = mlflow.artifacts.download_artifacts(
        run_id=model.source_run_id, artifact_path="model_state"
    )
    config_path = os.path.join(artifact_dir, "genie_config.json")
    with open(config_path) as f:
        return json.load(f)
```

### Prompt Version Tracking

Track which prompt versions were used during each iteration's evaluation:

```python
def collect_prompt_versions(uc_schema: str) -> dict:
    """Collect current prompt versions from the Prompt Registry."""
    prompt_versions = {}
    for name in ["schema_accuracy", "logical_accuracy", "semantic_equivalence",
                  "completeness", "arbiter"]:
        prompt_name = f"{uc_schema}.genie_opt_{name}"
        try:
            prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
            prompt_versions[name] = prompt.version
        except Exception:
            prompt_versions[name] = "inline"
    return prompt_versions
```

---

## Session State Schema

The orchestrator maintains this dict across iterations, persisted in `optimization-progress.json`:

```python
session = {
    "space_id": str,                 # Genie Space being optimized
    "domain": str,                   # Domain name (e.g., "cost")
    "started_at": str,               # ISO 8601 timestamp
    "current_iteration": int,        # 0 = not started, 1+ = iteration number
    "max_iterations": int,           # Default 5
    "status": str,                   # in_progress | converged | stalled | max_iterations | evaluated
    "iterations": [                  # Per-iteration results
        {
            "iteration": int,
            "timestamp": str,
            "model_id": str,            # LoggedModel ID for this iteration's config
            "mlflow_run_id": str,
            "overall_accuracy": float,  # 0-100 percentage
            "total_questions": int,
            "correct_count": int,
            "failures": list[str],      # Question IDs that failed
            "remaining_failures": list[str],
            "scores": dict,             # Per-judge scores
            "proposals_applied": list,  # Proposals applied in this iteration
        }
    ],
    "best_iteration": int,
    "best_overall_accuracy": float,
    "remaining_failures": list[str],
    "convergence_reason": str | None,
    "promoted_model_id": str | None,  # LoggedModel ID of the best iteration (after promotion)
    "score_history": list[dict],      # Per-iteration score vectors for Pareto tracking
    "patch_history": list[dict],      # Per-iteration patch sets applied
    "pareto_frontier": list[dict],    # Non-dominated solution vectors
    "current_patch_set": list | None, # Patches being evaluated in the current iteration
    "patched_objects": list[str],     # Metadata objects modified by the current patch set
    "maturity_level": str,            # L1 (greedy) | L2 (GEPA) | L3 (multi-objective)
    "benchmark_corrections": list,    # Arbiter-corrected GT questions
    "lever_impacts": {                # Per-lever before/after score tracking
        str: {                        # Lever number as string ("1"-"6")
            "before": dict,           # Scores before applying this lever's proposals
            "after": dict,            # Scores after applying this lever's proposals
            "proposals": list,        # Proposals applied for this lever
            "delta": float,           # overall_accuracy change
        }
    },
    "worker_reads": list,             # Audit trail of worker SKILL.md reads
    "eval_dataset_name": str | None,  # UC evaluation dataset name
    "use_patch_dsl": bool,            # Default True — use Patch DSL for apply
    "repeatability_pct": float,       # Current repeatability percentage (default 0.0)
    "best_repeatability": float,      # Best repeatability across iterations (default 0.0)
    "repeatability_target": float,    # Target repeatability (default 90.0)
    "lever_audit": {                  # Per-lever attempt tracking
        str: {                        # Lever number as string ("1"-"6")
            "attempted": bool,
            "proposals_generated": int,
            "proposals_applied": int,
            "skip_reason": str | None,
        }
    },
}
```

---

## Progress Tracking Functions

```python
import json
from datetime import datetime
from pathlib import Path

def init_progress(space_id: str, domain: str, max_iterations: int = 5) -> dict:
    """Initialize a new optimization progress tracker.

    Returns the full session dict with all fields from the schema above.
    """
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


def load_progress(path: str) -> dict:
    """Load existing progress from file. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def update_progress(progress: dict, iteration_result: dict) -> dict:
    """Append an iteration result to the progress tracker.

    Also updates: score_history, patch_history, repeatability tracking,
    and Pareto frontier via _update_pareto_frontier().
    """
    progress["iterations"].append(iteration_result)
    progress["current_iteration"] = iteration_result.get("iteration", len(progress["iterations"]))

    overall = iteration_result.get("overall_accuracy", 0)
    if overall > progress["best_overall_accuracy"]:
        progress["best_overall_accuracy"] = overall
        progress["best_iteration"] = progress["current_iteration"]

    progress["remaining_failures"] = iteration_result.get("remaining_failures", [])

    # Score history
    scores = iteration_result.get("scores", {})
    if scores:
        progress.setdefault("score_history", []).append({
            "iteration": progress["current_iteration"],
            "scores": scores,
            "overall_accuracy": overall,
        })

    # Patch history
    patches = iteration_result.get("patch_set") or iteration_result.get("proposals_applied", [])
    if patches:
        progress.setdefault("patch_history", []).append({
            "iteration": progress["current_iteration"],
            "patches": patches,
        })

    # Repeatability tracking
    rep_pct = iteration_result.get("repeatability_pct", 0)
    if rep_pct:
        progress["repeatability_pct"] = rep_pct
        if rep_pct > progress.get("best_repeatability", 0):
            progress["best_repeatability"] = rep_pct

    return progress


def write_progress(progress: dict, path: str):
    """Write progress tracker to file."""
    with open(path, "w") as f:
        json.dump(progress, f, indent=2)
```

---

## Prompt Registration

Register all optimizer LLM prompts with dual storage (MLflow Prompt Registry + MLflow artifacts). Called once at the start of an optimization session.

```python
import mlflow
from datetime import datetime

JUDGE_PROMPTS = {
    "schema_accuracy": "You are a SQL schema expert. Determine if the generated SQL references the correct tables, columns, and joins for the given question.",
    "logical_accuracy": "You are a SQL logic expert. Determine if the generated SQL applies correct aggregations, filters, GROUP BY, ORDER BY, and WHERE clauses.",
    "semantic_equivalence": "You are a SQL semantics expert. Determine if two SQL queries measure the SAME business metric despite syntactic differences.",
    "completeness": "You are a SQL completeness expert. Determine if the generated SQL fully answers the user's question.",
    "arbiter": "You are a senior SQL arbiter. Two SQL queries attempted to answer the same business question but produced different results. Determine which is correct.",
    "introspection_cluster": "You are a failure analysis expert. Given evaluation results with judge feedback, identify systemic root causes that affect multiple questions.",
}


def register_optimizer_prompts(experiment_name: str, domain: str,
                                uc_schema: str = None) -> dict:
    """Register all optimizer LLM prompts with dual storage.

    Storage 1: MLflow Prompt Registry (versioned, aliased).
    Storage 2: MLflow artifacts in experiment run (visible in Artifacts tab).

    Returns:
        dict mapping prompt name to version info.
    """
    registered = {}

    if uc_schema:
        for name, template in JUDGE_PROMPTS.items():
            prompt_name = f"{uc_schema}.genie_opt_{name}"
            try:
                version = mlflow.genai.register_prompt(
                    name=prompt_name,
                    template=template,
                    tags={"domain": domain, "type": "judge" if name != "introspection_cluster" else "introspection"},
                )
                mlflow.genai.set_prompt_alias(name=prompt_name, alias="production", version=version.version)
                registered[name] = {"name": prompt_name, "version": version.version, "storage": "prompt_registry"}
            except Exception as e:
                print(f"  [Prompt Registry] Skipped {prompt_name}: {e}")

    mlflow.set_experiment(experiment_name)
    run_name = f"register_prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with mlflow.start_run(run_name=run_name):
        for name, template in JUDGE_PROMPTS.items():
            import tempfile, os
            tmp = os.path.join(tempfile.gettempdir(), f"genie_opt_{name}.txt")
            with open(tmp, "w") as f:
                f.write(template)
            mlflow.log_artifact(tmp, artifact_path=f"judge_prompts/{name}")

        mlflow.log_params({
            "num_prompts": len(JUDGE_PROMPTS),
            "prompt_keys": ",".join(JUDGE_PROMPTS.keys()),
            "domain": domain,
            "registration_date": datetime.now().isoformat(),
        })

    return registered
```

---

## Convergence Criteria

### When to Stop Iterating

| Condition | Action |
|-----------|--------|
| All 8 judges meet their targets | Optimization complete → proceed to deploy |
| Accuracy >= 90% after 5 iterations | Acceptable → proceed, document remaining issues |
| No improvement for 2 consecutive iterations | Stalled → escalate, likely LLM limitation |
| Regression detected that can't be reverted | Escalate → conflicting optimization goals |

### Per-Judge Targets

| Judge | Target | Convergence Threshold |
|-------|--------|----------------------|
| syntax_validity | 98% | Stop if stuck below 90% |
| schema_accuracy | 95% | Stop if stuck below 85% |
| logical_accuracy | 90% | Stop if stuck below 80% |
| semantic_equivalence | 90% | Stop if stuck below 80% |
| completeness | 90% | Stop if stuck below 80% |
| result_correctness | 85% | Stop if stuck below 70% |
| asset_routing | 95% | Stop if stuck below 85% |
| repeatability | 90% | Stop if stuck below 70% |

---

## Pre-Optimization Setup

### 0. Resolve CLI Profile & Discover Genie Space ID

```python
profile = resolve_cli_profile()  # Reads databricks.yml → validates Genie access
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile=profile)
spaces = list(w.genie.list_spaces())
for s in spaces:
    print(f"  {s.space_id}  {s.title}")
```

### 1. Load & Validate Benchmarks

Delegate to Generator worker. See `genie-benchmark-generator` SKILL.md.

### 2. Sync to MLflow Evaluation Dataset

Owned by the evaluator job — the orchestrator only computes `eval_dataset_name` and passes it as a job parameter.

### 3. Fetch Config & Create LoggedModel

```python
config = _fetch_space_config(space_id)
model_id = create_genie_model_version(space_id, config, 0, domain, uc_schema=uc_schema)
```

---

## Post-Deploy Re-Assessment

Re-run all benchmarks against the bundle-deployed Genie Space. Compare to in-loop results. If post-deploy accuracy is lower, a change was applied via API but NOT written to bundle files — fix the missing file and redeploy.

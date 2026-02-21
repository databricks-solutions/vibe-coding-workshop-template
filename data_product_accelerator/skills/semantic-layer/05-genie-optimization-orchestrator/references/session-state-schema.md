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

def verify_mlflow_tracking(experiment_name: str, host: str = None) -> dict:
    """Create MLflow experiment and verify it is accessible.

    Call this ONCE at the start of every optimization session.
    Raises RuntimeError if MLflow is not configured for Databricks.

    Returns:
        dict with experiment_id and experiment_url
    """
    tracking_uri = mlflow.get_tracking_uri()
    if tracking_uri != "databricks" and not tracking_uri.startswith("databricks"):
        if not os.environ.get("DATABRICKS_HOST"):
            raise RuntimeError(
                "MLflow not configured for Databricks. Set DATABRICKS_HOST, "
                "DATABRICKS_TOKEN, MLFLOW_TRACKING_URI='databricks'"
            )

    mlflow.set_experiment(experiment_name)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    assert experiment is not None, "Experiment creation failed"

    host = host or os.environ.get("DATABRICKS_HOST", "")
    url = f"{host}/#mlflow/experiments/{experiment.experiment_id}"
    print(f"MLflow Experiment: {experiment_name}")
    print(f"Experiment ID:     {experiment.experiment_id}")
    print(f"Experiment URL:    {url}")
    return {"experiment_id": experiment.experiment_id, "experiment_url": url}
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

## Metadata Snapshot

Before each optimization iteration, capture the current Genie Space configuration and store as an MLflow artifact for before/after comparison and rollback.

```python
def snapshot_genie_metadata(space_id: str, experiment_name: str, version_tag: str) -> str:
    """Capture current Genie Space config as an MLflow artifact.

    Returns:
        The artifact URI.
    """
    import json, tempfile, os

    config_json = _fetch_space_config(space_id)

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=f"snapshot-{version_tag}") as run:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="genie_snapshot_"
        )
        json.dump(config_json, tmp, indent=2)
        tmp.close()
        mlflow.log_artifact(tmp.name, artifact_path="snapshots")
        os.unlink(tmp.name)
        return f"runs:/{run.info.run_id}/snapshots"


def _fetch_space_config(space_id: str) -> dict:
    """GET Genie Space config via SDK."""
    import json
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    resp = w.api_client.do(
        "GET", f"/api/2.0/genie/spaces/{space_id}"
    )
    return resp
```

---

## Genie Space Version Tracking (LoggedModel)

Each optimization iteration creates an MLflow `LoggedModel` to track the exact Genie Space configuration that was evaluated. This connects config snapshots, evaluation results, and Genie API traces in the MLflow Versions tab.

```python
import hashlib
import json
import tempfile
import os

def create_genie_model_version(space_id: str, config: dict,
                                iteration: int, domain: str,
                                patch_set=None, parent_model_id=None,
                                prompt_versions=None) -> str:
    """Create a LoggedModel version for the current Genie Space state.

    The LoggedModel acts as a metadata hub linking this specific config
    to its evaluation results, Genie API traces, applied patches, and
    prompt versions. Call BEFORE evaluation so that
    mlflow.genai.evaluate(model_id=...) links correctly.

    Args:
        space_id: Genie Space ID.
        config: Full Genie Space configuration dict from the API.
        iteration: Current optimization iteration number.
        domain: Business domain name.
        patch_set: List of patch dicts applied in this iteration (None for baseline).
        parent_model_id: LoggedModel ID of the previous iteration (lineage chain).
        prompt_versions: Dict mapping judge name to prompt version used.

    Returns:
        model_id (str) for passing to mlflow.genai.evaluate().
    """
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    model_name = f"genie-{domain}-iter{iteration}-{config_hash}"

    active_model = mlflow.set_active_model(name=model_name)

    instructions = config.get("general_instructions", "")
    data_assets = config.get("data_assets", [])

    params = {
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
        "patch_types": ",".join(p["type"] for p in patch_set) if patch_set else "none",
        "patch_risk_levels": ",".join(
            sorted(set(p.get("risk_level", "unknown") for p in patch_set))
        ) if patch_set else "none",
        "parent_model_id": parent_model_id or "none",
        "prompt_versions": json.dumps(prompt_versions) if prompt_versions else "{}",
    }
    mlflow.log_model_params(model_id=active_model.model_id, params=params)

    tmp_path = os.path.join(tempfile.gettempdir(), f"genie_config_iter{iteration}.json")
    with open(tmp_path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    mlflow.log_artifact(tmp_path, artifact_path="genie_config")
    os.unlink(tmp_path)

    if patch_set:
        patch_path = os.path.join(tempfile.gettempdir(), f"patch_set_iter{iteration}.json")
        with open(patch_path, "w") as f:
            json.dump(patch_set, f, indent=2, default=str)
        mlflow.log_artifact(patch_path, artifact_path="config_diffs")
        os.unlink(patch_path)

    print(f"  LoggedModel: {model_name} (model_id={active_model.model_id})")
    return active_model.model_id
```

The updated `snapshot_genie_metadata()` now returns both the artifact URI and the `model_id`:

```python
def snapshot_genie_metadata(space_id: str, experiment_name: str,
                             version_tag: str, iteration: int = 0,
                             domain: str = "unknown") -> dict:
    """Capture current Genie Space config and create a LoggedModel version.

    Returns:
        dict with artifact_uri and model_id.
    """
    import json, tempfile, os

    config_json = _fetch_space_config(space_id)

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=f"snapshot-{version_tag}") as run:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="genie_snapshot_"
        )
        json.dump(config_json, tmp, indent=2, default=str)
        tmp.close()
        mlflow.log_artifact(tmp.name, artifact_path="snapshots")
        os.unlink(tmp.name)
        artifact_uri = f"runs:/{run.info.run_id}/snapshots"

    model_id = create_genie_model_version(space_id, config_json, iteration, domain)

    return {"artifact_uri": artifact_uri, "model_id": model_id}
```

---

## LoggedModel Lifecycle: Promote & Rollback

After the optimization loop converges, promote the best-performing LoggedModel. When P0 gate fails, rollback to the parent model's config.

```python
def promote_best_model(session: dict):
    """Tag the best-performing LoggedModel for promotion.

    Call after the optimization loop converges or reaches max iterations.
    The promoted model appears with a "promoted: true" tag in the
    MLflow Versions tab for easy identification.
    """
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
    print(f"  Promoted LoggedModel: {best_model_id}")


def rollback_to_model(model_id: str, space_id: str) -> dict:
    """Restore Genie Space config from a LoggedModel's artifact.

    Used when P0 gate fails and the orchestrator needs to revert
    to the previous iteration's configuration.

    Returns:
        The Genie Space config dict from the model's artifact, or None on failure.
    """
    model = mlflow.get_logged_model(model_id=model_id)
    config_artifact = mlflow.artifacts.download_artifacts(
        run_id=model.source_run_id, artifact_path="genie_config"
    )
    import os
    for f in os.listdir(config_artifact):
        if f.endswith(".json"):
            with open(os.path.join(config_artifact, f)) as fh:
                return json.load(fh)
    return None
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
    "cli_profile": str | None,       # Databricks CLI profile (from databricks.yml)
    "started_at": str,               # ISO 8601 timestamp
    "experiment_name": str,          # MLflow experiment path
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
    "lever_impacts": {                # Per-lever before/after score tracking (Gap 15)
        int: {                        # Lever number (1-6)
            "before": dict,           # Scores before applying this lever's proposals
            "after": dict,            # Scores after applying this lever's proposals
            "proposals": list,        # Proposals applied for this lever
            "delta": float,           # overall_accuracy change
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
    """Initialize a new optimization progress tracker."""
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
        "lever_impacts": {},
    }


def load_progress(path: str) -> dict:
    """Load existing progress from file. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def update_progress(progress: dict, iteration_result: dict) -> dict:
    """Append an iteration result to the progress tracker."""
    progress["iterations"].append(iteration_result)
    progress["current_iteration"] = iteration_result.get("iteration", len(progress["iterations"]))

    overall = iteration_result.get("overall_accuracy", 0)
    if overall > progress["best_overall_accuracy"]:
        progress["best_overall_accuracy"] = overall
        progress["best_iteration"] = progress["current_iteration"]

    progress["remaining_failures"] = iteration_result.get("remaining_failures", [])
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
                print(f"  [Prompt Registry] Registered: {prompt_name} v{version.version}")
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
            print(f"  [MLflow Artifact] Logged: judge_prompts/{name}")

        mlflow.log_params({
            "num_prompts": len(JUDGE_PROMPTS),
            "prompt_keys": ",".join(JUDGE_PROMPTS.keys()),
            "domain": domain,
            "registration_date": datetime.now().isoformat(),
        })

    print(f"\n  Registered {len(JUDGE_PROMPTS)} prompts (artifacts in experiment: {experiment_name})")
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

## Pre-Optimization Setup (from optimization-workflow.md)

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

```python
dataset_name = sync_yaml_to_mlflow_dataset(yaml_path, uc_schema, domain)
```

### 3. Snapshot Current Metadata & Create LoggedModel

```python
snapshot = snapshot_genie_metadata(space_id, experiment_name, "pre-optimization",
                                   iteration=0, domain=domain)
model_id = snapshot["model_id"]  # Pass to evaluator for linked evaluation
```

---

## Post-Deploy Re-Assessment

Re-run all benchmarks against the bundle-deployed Genie Space. Compare to in-loop results. If post-deploy accuracy is lower, a change was applied via API but NOT written to bundle files — fix the missing file and redeploy.

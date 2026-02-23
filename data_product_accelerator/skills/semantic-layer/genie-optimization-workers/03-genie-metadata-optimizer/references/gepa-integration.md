# GEPA Integration Reference

Dedicated reference for GEPA-powered optimization of Genie Space metadata. Covers GEPA L2 (Genie Evolution through Prompt Adaptation) with patch set JSON candidates, and judge prompt optimization via `mlflow.genai.optimize_prompts()`.

> **GEPA addresses Lever 6 (Genie Instructions + Example SQLs) only.** Run L1 introspection for Levers 1-5 first. GEPA is the lowest-priority lever with a ~4000 character limit. Only invoke GEPA after Levers 1-5 have been exhausted and scores are still below target. See orchestrator hard constraint #14.

---

## Two GEPA Use Cases

| Use Case | API | Candidate | Evaluator | Output |
|----------|-----|-----------|-----------|--------|
| **Metadata optimization (L2)** | `run_gepa_optimization()` | Patch set JSON (structured patches) | `GenieMetadataAdapter.evaluate()` | Best patch set |
| **Judge prompt optimization** | `mlflow.genai.optimize_prompts()` | Judge prompt template string | MLflow evaluation harness | Optimized prompt version in Registry |

These are always separate — never run both in the same optimization call.

---

## Tier Selection Criteria

| Tier | Engine | Prerequisites | When to Use |
|------|--------|---------------|-------------|
| **1** | GEPA L2 (patch sets) | `use_gepa=True`, judge feedbacks | Optimizing metadata via structured patch sets |
| **2** | LLM Introspection (no GEPA) | None | Primarily optimizing UC table/column descriptions |
| **3** | SIMBA Judge Alignment | Human labels available | Judges are the bottleneck (low agreement) |
| **Fallback** | `dspy.MIPROv2` | `dspy`, ~50+ examples | GEPA too complex for the use case |

---

## GEPA L2: Metadata Optimization with Patch Set JSON Candidates

GEPA L2 uses structured patch sets (not raw text fields) as candidates. The `GenieMetadataAdapter` wraps GEPA optimization with apply → evaluate → rollback semantics.

### GenieMetadataAdapter Class

```python
import copy
import json
from typing import Callable


class GenieMetadataAdapter:
    """Wraps GEPA optimization with structured patch set JSON candidates.

    Candidates are patch sets (lists of patch dicts), not text fields.
    Each evaluation applies patches to a config copy, runs the evaluator,
    returns score + ASI trajectories, then rolls back.
    """

    def __init__(
        self,
        space_id: str,
        config: dict,
        judge_suite: dict,
        evaluator_fn: Callable[[dict, dict], tuple[float, dict]],
    ):
        """Initialize with Genie Space config and evaluation function.

        Args:
            space_id: Genie Space ID.
            config: Current Genie metadata config (will be copied for each eval).
            judge_suite: Judge suite for scoring (e.g., from create_judge_suite()).
            evaluator_fn: Function(config_patched, example) -> (score, asi_dict).
        """
        self.space_id = space_id
        self.config = config
        self.judge_suite = judge_suite
        self.evaluator_fn = evaluator_fn

    def evaluate(self, patch_set_json: list[dict]) -> tuple[float, list[dict]]:
        """Apply patches to config copy, run evaluator, return score + ASI trajectories, then rollback.

        Args:
            patch_set_json: List of patch dicts (type, scope, object_id, etc.).

        Returns:
            Tuple of (overall_score: float, asi_trajectories: list of ASI dicts).
        """
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

    def make_reflective_dataset(self, eval_results: list[dict]) -> list[dict]:
        """Create a reflective dataset from evaluation results for GEPA learning.

        Args:
            eval_results: List of dicts with keys: patch_set, score, asi_trajectories.

        Returns:
            List of examples for GEPA reflection LM (patch_set, score, rationales, etc.).
        """
        dataset = []
        for r in eval_results:
            patch_set = r.get("patch_set", [])
            score = r.get("score", 0.0)
            trajectories = r.get("asi_trajectories", [])

            rationales = []
            for asi in trajectories:
                rationales.extend(asi.get("judge_rationales", {}).values())

            dataset.append({
                "patch_set": patch_set,
                "score": score,
                "rationales": rationales,
                "asi_trajectories": trajectories,
            })
        return dataset

    def generate_candidates(self, n: int = 5) -> list[list[dict]]:
        """Generate n candidate patch set JSONs from current failures.

        Uses judge feedbacks and failure taxonomy to propose patch sets.
        Returns list of patch sets (each is a list of patch dicts).
        """
        failures = self._get_current_failures()
        candidates = []

        for _ in range(n):
            patch_set = propose_patch_set_from_asi(failures, self.config)
            if not patch_set and failures:
                fixes = []
                for f in failures:
                    cf = f.get("counterfactual_fix") or f.get("counterfactual_fixes") or []
                    fixes.extend(cf if isinstance(cf, list) else [cf] if cf else [])
                patch_set = _synthesize_patches_from_fixes(fixes, failures, self.config)
            if patch_set and validate_patch_set(patch_set)[0]:
                candidates.append(patch_set)

        return candidates[:n]

    def _get_benchmark_examples(self, patch_set: list = None) -> list:
        """Return benchmark examples. When no live API, uses patch_set as single example: [{"patch_set": patch_set, "asi": {}}]."""
        if patch_set is not None:
            return [{"patch_set": patch_set, "asi": {}}]
        return getattr(self.config, "_benchmark_examples", [])

    def _get_current_failures(self) -> list:
        """Return current judge feedback failures from config._judge_feedbacks."""
        return self.config.get("_judge_feedbacks", [])
```

### run_gepa_optimization — Top-Level Function

```python
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

    Gated behind use_gepa=True (default False for safety when called from CLI).

    Args:
        space_id: Genie Space ID.
        config: Current Genie metadata config.
        judge_feedbacks: List of judge feedback dicts (value, blame_set, etc.).
        judge_suite: Judge suite for scoring (from create_judge_suite()). Optional.
        max_rounds: Max optimization rounds (default 3).
        use_gepa: If False, returns None immediately (safety gate).

    Returns:
        Best patch set (list of patch dicts) or None.
    """
    if not use_gepa:
        return None

    judge_suite = judge_suite or {}

    def evaluator_fn(config_patched: dict, example: dict) -> tuple[float, dict]:
        # Apply config_patched to space, run query, score with judges
        score, asi = _evaluate_config_against_example(
            space_id, config_patched, example, judge_suite
        )
        return score, asi

    adapter = GenieMetadataAdapter(
        space_id=space_id,
        config=config,
        judge_suite=judge_suite,
        evaluator_fn=evaluator_fn,
    )

    # Attach failures for generate_candidates
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

        # Multi-objective scoring: score - 0.1 * blast_radius
        for r in eval_results:
            blast = len(set(p.get("object_id") or p.get("target") for p in r["patch_set"]))
            r["mo_score"] = r["score"] - 0.1 * blast

        best_by_mo = max(eval_results, key=lambda x: x["mo_score"])
        if best_by_mo["mo_score"] > (best_score - 0.1 * 5):
            best_patch_set = best_by_mo["patch_set"]
            best_score = best_by_mo["score"]

    return best_patch_set
```

### Helper Functions (Reference)

```python
NON_EXPORTABLE_FIELDS = {
    "id", "title", "description", "creator", "creator_id",
    "updated_by", "updated_at", "created_at", "warehouse_id",
    "execute_as_user_id", "space_status",
}


def strip_non_exportable_fields(config: dict) -> dict:
    """Remove fields from GET response that are invalid in PATCH serialized_space.

    The GET /api/2.0/genie/spaces/{id} response includes top-level metadata
    fields that are NOT part of the GenieSpaceExport protobuf. Including them
    causes: InvalidParameterValue: Cannot find field: <field> in message
    databricks.datarooms.export.GenieSpaceExport

    MUST be called before sort_genie_config() when building a PATCH payload.
    """
    return {k: v for k, v in config.items() if k not in NON_EXPORTABLE_FIELDS}


def _apply_patch_set_to_config(config: dict, patch_set: list[dict]) -> None:
    """Apply patch set to config in-place. Implementation in metadata_optimizer; no separate _apply_single_patch."""
    for p in patch_set:
        # Inline logic: add_instruction, add_synonym, update_description, etc. (see metadata_optimizer._apply_patch_set_to_config)
        pass


def validate_patch_set(patch_set: list[dict]) -> tuple[bool, list[str]]:
    """Validate patch set (import from metadata_optimizer)."""
    from metadata_optimizer import validate_patch_set as _validate
    return _validate(patch_set)


def propose_patch_set_from_asi(failures: list, config: dict, target_lever: int | None = None) -> list[dict]:
    """Synthesize patch set from failures. Import from metadata_optimizer."""
    from metadata_optimizer import propose_patch_set_from_asi as _propose
    return _propose(failures, config, target_lever)
```

### Helper Function Sources

| Function | Source File | Notes |
|----------|-----------|-------|
| `strip_non_exportable_fields()` | Self-contained above; also in `optimization_applier.py` | MUST call before any PATCH |
| `sort_genie_config()` | `optimization_applier.py` or `control-levers.md` | MUST call after `strip_non_exportable_fields()` |
| `validate_patch_set()` | `metadata_optimizer.py` | Import from optimizer script (no underscore prefix) |
| `propose_patch_set_from_asi()` | `metadata_optimizer.py` | Synthesize patch set from failures |
| `_synthesize_patches_from_fixes()` | `metadata_optimizer.py` | Internal: map counterfactual fixes to patches |
| `_apply_patch_set_to_config()` | `metadata_optimizer.py` | Apply patches in-place; no separate _apply_single_patch |

### Feature Gate

GEPA L2 is **gated behind `use_gepa=True`** (default `False` for safety). The CLI exposes `--use-gepa` to enable it:

```bash
python metadata_optimizer.py --eval-results eval.json --metadata-snapshot snap.json --output proposals.json --use-gepa
```

---

## Judge Prompt Optimization

Separate from metadata optimization. Uses `mlflow.genai.optimize_prompts()` with GEPA under the hood.

```python
import mlflow

def optimize_judge_prompts(
    uc_schema: str,
    judge_names: list,
    eval_dataset_name: str,
    space_id: str,
) -> dict:
    """Optimize judge prompt templates using GEPA via MLflow.

    Requires MLflow >= 3.5.0. Optimizes prompt text, auto-registers
    new versions in the Prompt Registry.

    Args:
        uc_schema: Unity Catalog schema for prompts.
        judge_names: List of judge names to optimize (e.g., ["schema_accuracy"]).
        eval_dataset_name: MLflow Evaluation Dataset for scoring.
        space_id: Genie Space ID.

    Returns:
        dict mapping judge name to optimized prompt version.
    """
    from mlflow.genai import GepaPromptOptimizer

    results = {}
    for name in judge_names:
        prompt_name = f"{uc_schema}.genie_opt_{name}"

        try:
            optimized = mlflow.genai.optimize_prompts(
                target_prompt=prompt_name,
                optimizer=GepaPromptOptimizer(),
                eval_dataset=eval_dataset_name,
            )

            new_version = mlflow.genai.register_prompt(
                name=prompt_name,
                template=optimized.template,
                tags={"optimized_by": "gepa", "source_alias": "production"},
            )

            mlflow.genai.set_prompt_alias(
                name=prompt_name, alias="staging", version=new_version.version
            )

            results[name] = {
                "version": new_version.version,
                "alias": "staging",
                "status": "optimized",
            }
        except Exception as e:
            results[name] = {"status": "failed", "error": str(e)}

    return results
```

---

## Rate Limit Budget

With `cache_evaluation=True`, GEPA avoids re-querying Genie for identical metadata+question pairs.

| Benchmark Size | Calls/Iteration | Total (5 iter) | Wall Clock |
|---------------|----------------|-----------------|------------|
| 15 questions | ~3 min | ~15 min | ~15 min |
| 50 questions | ~10 min | ~50 min | ~50 min |
| 150 questions | ~30 min | ~2.5 hrs | ~2.5 hrs |

Set `max_metric_calls` in `GEPAConfig` to stay within budget. The default of 150 allows roughly 10 candidate evaluations across 15 questions.

---

## GEPA Configuration Reference

```python
GEPAConfig(
    engine=EngineConfig(
        max_metric_calls=150,       # Total Genie API call budget
        cache_evaluation=True,      # Avoid re-querying same metadata+question
    ),
    reflection=ReflectionConfig(
        reflection_lm="databricks:/databricks-claude-sonnet-4-6",
    ),
)
```

Key settings:
- `cache_evaluation=True` is critical for Genie's 12s rate limit
- `reflection_lm` reads judge rationales (ASI) to propose metadata mutations
- `max_metric_calls` should match your rate limit budget

---

## Fallback: DSPy MIPROv2

If GEPA is too complex or unavailable, use DSPy's MIPROv2 as a fallback. Requires ~50+ benchmark examples for Bayesian optimization.

```python
import dspy

def run_dspy_fallback(train_examples: list, eval_fn, prompt_template: str) -> str:
    """Fallback optimizer using DSPy MIPROv2."""
    optimizer = dspy.teleprompt.MIPROv2(
        metric=eval_fn,
        num_candidates=5,
        num_threads=1,
    )

    class GenieModule(dspy.Module):
        def __init__(self):
            self.predict = dspy.Predict("question -> sql")

        def forward(self, question):
            return self.predict(question=question)

    module = GenieModule()
    optimized = optimizer.compile(module, trainset=train_examples)
    return optimized
```

# Prompt Registry Patterns

All optimizer LLM prompts are managed in the MLflow Prompt Registry (Unity Catalog). This enables versioning, aliases, GEPA optimization, and rollback.

---

## Registered Prompts

| Prompt Name | Type | Used By | Description |
|-------------|------|---------|-------------|
| `genie_opt_schema_accuracy` | judge | Layer 1 | Evaluates SQL table/column/join correctness |
| `genie_opt_logical_accuracy` | judge | Layer 1 | Evaluates SQL aggregation/filter/grouping logic |
| `genie_opt_semantic_equivalence` | judge | Layer 1 | Determines if two SQLs measure the same business metric |
| `genie_opt_completeness` | judge | Layer 1 | Checks if SQL fully answers the question |
| `genie_opt_arbiter` | judge | Layer 3 | Determines which SQL is correct when results disagree |
| `genie_opt_introspection_cluster` | introspection | Failure analysis | Identifies systemic root causes across failures |

---

## Lifecycle Flow

```
1. REGISTER    → mlflow.genai.register_prompt(name, template, tags)
2. SET ALIAS   → mlflow.genai.set_prompt_alias(name, "production", version)
3. LOAD        → mlflow.genai.load_prompt("prompts:/{name}@production")
4. USE         → make_judge(instructions=prompt.template, ...)
5. OPTIMIZE    → mlflow.genai.optimize_prompts() with GepaPromptOptimizer
6. RE-REGISTER → mlflow.genai.register_prompt(name, optimized_template)
7. STAGE       → mlflow.genai.set_prompt_alias(name, "staging", new_version)
8. TEST        → Evaluate with staging alias, compare to production
9. PROMOTE     → mlflow.genai.set_prompt_alias(name, "production", new_version)
```

---

## Initial Registration

Run on first optimization of a domain:

```python
registered = register_optimizer_prompts(uc_schema, domain)
```

This registers all 6 prompts with `production` alias. See `optimization-code-patterns.md` §Prompt Registry for the implementation.

---

## Loading Prompts by Alias

```python
prompts = load_judge_prompts(uc_schema, alias="production")
schema_judge = make_judge(
    name="schema_accuracy",
    instructions=prompts["schema_accuracy"],
    model="databricks:/databricks-claude-sonnet-4-6",
)
```

The alias mechanism enables safe rollback: if `staging` performs worse than `production`, simply don't promote.

---

## GEPA Judge Prompt Optimization

Uses `mlflow.genai.optimize_prompts()` with `GepaPromptOptimizer` to evolve judge prompt text. Requires MLflow >= 3.5.0.

```python
results = optimize_judge_prompts(
    uc_schema=uc_schema,
    judge_names=["schema_accuracy", "logical_accuracy"],
    eval_dataset_name=dataset_name,
    space_id=space_id,
)
```

Optimized prompts are registered as new versions and aliased to `staging`. After testing, promote to `production`.

See `gepa-integration.md` §Judge Prompt Optimization for the full implementation.

---

## Updating Judge Prompts

After introspection reveals a judge needs refinement (e.g., false negatives), update the prompt version:

```python
def update_judge_prompt(uc_schema: str, judge_name: str, new_template: str, tags: dict = None) -> int:
    """Register a new version of a judge prompt and alias it to staging."""
    prompt_name = f"{uc_schema}.genie_opt_{judge_name}"
    base_tags = {"type": "judge", "optimized_by": "introspection"}
    if tags:
        base_tags.update(tags)

    version = mlflow.genai.register_prompt(
        name=prompt_name,
        template=new_template,
        tags=base_tags,
    )
    mlflow.genai.set_prompt_alias(prompt_name, "staging", version.version)
    print(f"  [Prompt] {prompt_name} v{version.version} → staging")
    return version.version
```

## Promoting Optimized Prompts

After verifying a staging prompt outperforms production:

```python
def promote_optimized_prompt(uc_schema: str, judge_name: str, version: int):
    """Promote a staging prompt version to production alias."""
    prompt_name = f"{uc_schema}.genie_opt_{judge_name}"
    mlflow.genai.set_prompt_alias(prompt_name, "production", version)
    print(f"  [Prompt] {prompt_name} v{version} → production")
```

**Workflow:** `update_judge_prompt()` → run evaluation with staging → compare → `promote_optimized_prompt()` if better.

---

## Rollback Pattern

If an optimized prompt performs worse:

```python
# Find the previous production version
previous_version = current_production_version - 1

# Roll back
mlflow.genai.set_prompt_alias(
    name=f"{uc_schema}.genie_opt_{judge_name}",
    alias="production",
    version=previous_version,
)
```

---

## Tag Conventions

All registered prompts use these tags:

| Tag | Values | Description |
|-----|--------|-------------|
| `domain` | cost, reliability, etc. | Domain this prompt was optimized for |
| `type` | judge, introspection | Prompt category |
| `optimized_by` | human, gepa | Who created this version |
| `iteration` | 1, 2, 3, ... | Which optimization iteration produced it |

---

## Prompt-to-Experiment Lineage

Link the Prompt Registry to MLflow experiments:

```python
mlflow.set_experiment_tags({
    "mlflow.promptRegistryLocation": uc_schema,
    "domain": domain,
})
```

This enables navigating from experiment results → prompts used → prompt versions in the MLflow UI.

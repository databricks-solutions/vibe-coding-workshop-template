# A/B Testing with Prompt Registry Aliases

> Complete reference for running champion/challenger prompt experiments using
> MLflow Prompt Registry aliases, side-by-side evaluation, and safe promotion.

---

## Concept

The Prompt Registry stores every template as an immutable, monotonically
versioned object. **Aliases** are mutable pointers to a specific version
number, giving you named slots (`production`, `staging`, `canary`) that
decouple deployment from registration.

A/B testing exploits this by binding two aliases to different template
versions and evaluating them against the same dataset:

```
prompt_name @ production  →  version 3  (champion)
prompt_name @ staging     →  version 4  (challenger)
```

---

## Champion / Challenger Alias Setup

### Step 1 — Register the Challenger

The champion is already in the registry with `production` pointing to it.
Register a new version of the **same prompt name** for the challenger:

```python
import mlflow.genai

prompt_name = "main.genie_optimization.genie_opt_syntax_validity"

challenger_version = mlflow.genai.register_prompt(
    name=prompt_name,
    template=(
        "You are a SQL syntax expert. Evaluate the following SQL.\n\n"
        "SQL: {{ sql_text }}\n\n"
        "Respond with a JSON object: {\"score\": 0 or 1, \"rationale\": \"...\"}"
    ),
    commit_message="Challenger: stricter scoring rubric with rationale",
    tags={"experiment": "ab-syntax-v4", "role": "challenger"},
)
print(f"Challenger registered as version {challenger_version.version}")
```

### Step 2 — Bind the Staging Alias

```python
mlflow.genai.set_prompt_alias(
    name=prompt_name,
    alias="staging",
    version=challenger_version.version,
)
```

Now:

| Alias | Version | Role |
|-------|---------|------|
| `production` | 3 | Champion |
| `staging` | 4 | Challenger |

### Step 3 — Verify Both Aliases Resolve

```python
champion = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
challenger = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@staging")

assert champion.version != challenger.version, "Aliases should point to different versions"
print(f"Champion v{champion.version}: {champion.template[:60]}...")
print(f"Challenger v{challenger.version}: {challenger.template[:60]}...")
```

---

## Side-by-Side Evaluation Workflow

### Approach A — Separate Evaluation Runs

Run the evaluation harness twice, once per alias, and compare metrics:

```python
import mlflow

ALIASES = ["production", "staging"]
results = {}

for alias in ALIASES:
    prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{alias}")

    with mlflow.start_run(run_name=f"eval-{alias}-v{prompt.version}"):
        mlflow.log_param("prompt_alias", alias)
        mlflow.log_param("prompt_version", prompt.version)

        scores = evaluate_prompt(prompt.template, eval_dataset)

        mlflow.log_metrics({
            "accuracy": scores["accuracy"],
            "avg_latency_ms": scores["avg_latency_ms"],
            "judge_agreement": scores["judge_agreement"],
        })
        results[alias] = scores

print(f"Champion accuracy:   {results['production']['accuracy']:.3f}")
print(f"Challenger accuracy: {results['staging']['accuracy']:.3f}")
```

### Approach B — Interleaved Evaluation

For statistical rigor, evaluate both prompts on each example within a
single run:

```python
import random

with mlflow.start_run(run_name="ab-test-interleaved"):
    champion_prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
    challenger_prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@staging")

    champion_scores = []
    challenger_scores = []

    for example in eval_dataset:
        order = random.choice(["champion_first", "challenger_first"])
        c_score = score_with_prompt(champion_prompt.template, example)
        s_score = score_with_prompt(challenger_prompt.template, example)
        champion_scores.append(c_score)
        challenger_scores.append(s_score)

    mlflow.log_metrics({
        "champion_mean": sum(champion_scores) / len(champion_scores),
        "challenger_mean": sum(challenger_scores) / len(challenger_scores),
        "champion_version": champion_prompt.version,
        "challenger_version": challenger_prompt.version,
    })
```

---

## Metrics Comparison Across Prompt Versions

When comparing prompt versions, track these metrics:

| Metric | Description | Better when |
|--------|-------------|-------------|
| Accuracy | % of correct judgments against ground truth | Higher |
| Judge agreement | % agreement with human-labeled gold set | Higher |
| Avg latency (ms) | Mean LLM response time | Lower |
| Token count | Mean input + output tokens | Lower (cost) |
| Parse success rate | % of responses that parse as valid JSON | Higher |
| False positive rate | % of incorrect "pass" judgments | Lower |
| False negative rate | % of incorrect "fail" judgments | Lower |

### Decision Framework

```
IF challenger.accuracy > champion.accuracy + SIGNIFICANCE_THRESHOLD
   AND challenger.parse_success >= champion.parse_success
   AND challenger.avg_latency <= champion.avg_latency * 1.2  # 20% latency budget
THEN promote challenger
ELSE keep champion
```

---

## Promotion: Moving the Winner to Production

```python
winner_alias = "staging"
winner_version = challenger_version.version  # determined by evaluation

mlflow.genai.set_prompt_alias(
    name=prompt_name,
    alias="production",
    version=winner_version,
)
print(f"Promoted version {winner_version} to production")
```

After promotion, all callers using `prompts:/{name}@production` automatically
pick up the new version — no code changes or redeployments needed.

### Clean Up the Staging Alias (Optional)

```python
mlflow.genai.delete_prompt_alias(
    name=prompt_name,
    alias="staging",
)
```

---

## Rollback

If the promoted version causes regressions, roll back by pointing
`production` at the previous version:

```python
previous_champion_version = 3

mlflow.genai.set_prompt_alias(
    name=prompt_name,
    alias="production",
    version=previous_champion_version,
)
print(f"Rolled back production to version {previous_champion_version}")
```

Rollback is instant because aliases are mutable pointers. No prompt data
is deleted or modified.

---

## Full Example: Register Two Versions, Evaluate, Promote

```python
import mlflow
import mlflow.genai

CATALOG = "main"
SCHEMA = "genie_optimization"
UC_SCHEMA = f"{CATALOG}.{SCHEMA}"
PROMPT_NAME = f"{UC_SCHEMA}.genie_opt_syntax_validity"

mlflow.set_experiment("/Shared/genie-optimization/ab-test")
mlflow.set_experiment_tags({"mlflow.promptRegistryLocation": UC_SCHEMA})

# -- Register champion (or it already exists) --
v1 = mlflow.genai.register_prompt(
    name=PROMPT_NAME,
    template="Score this SQL for correctness: {{ sql_text }}\nReturn JSON: {\"score\": 0 or 1}",
    commit_message="Champion: concise scoring template",
    tags={"role": "champion"},
)
mlflow.genai.set_prompt_alias(name=PROMPT_NAME, alias="production", version=v1.version)

# -- Register challenger --
v2 = mlflow.genai.register_prompt(
    name=PROMPT_NAME,
    template=(
        "You are a SQL validation expert.\n\n"
        "SQL: {{ sql_text }}\n\n"
        "Evaluate syntax correctness. Respond with JSON:\n"
        "{\"score\": 0 or 1, \"rationale\": \"<one sentence>\"}"
    ),
    commit_message="Challenger: added rationale field",
    tags={"role": "challenger"},
)
mlflow.genai.set_prompt_alias(name=PROMPT_NAME, alias="staging", version=v2.version)

# -- Evaluate both --
aliases = {"production": v1.version, "staging": v2.version}
scores = {}

for alias, ver in aliases.items():
    prompt = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@{alias}")
    with mlflow.start_run(run_name=f"eval-{alias}-v{ver}", nested=True):
        result = evaluate_prompt(prompt.template, eval_dataset)
        mlflow.log_metrics(result)
        scores[alias] = result

# -- Promote winner --
if scores["staging"]["accuracy"] > scores["production"]["accuracy"] + 0.02:
    mlflow.genai.set_prompt_alias(name=PROMPT_NAME, alias="production", version=v2.version)
    print(f"Promoted challenger v{v2.version} to production")
else:
    print(f"Champion v{v1.version} retained")
```

---

## Source References

- `config.py` line 2422: `PROMPT_ALIAS = "production"` — the default alias
  used by all production loaders.
- `evaluation.py` lines 2253–2257: `set_prompt_alias` call after registration.
- `evaluation.py` lines 306–321: `_link_prompt_to_trace()` which resolves
  `@production` then falls back to `@latest`.

## Related References

- [uc-schema-linkage.md](uc-schema-linkage.md) — prerequisite: tag setup.
- [loading-patterns.md](loading-patterns.md) — how `load_prompt` resolves aliases.
- [ownership-conflict-handling.md](ownership-conflict-handling.md) — what
  happens when registration fails due to ownership.

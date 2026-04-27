# Registered Scorers: Complete Lifecycle Reference

Production-grade scorer management for MLflow 3.10+ on Databricks. Covers
the full lifecycle from creation through retirement, sampling strategies,
serialization constraints, and multi-turn judges.

> **Source**: [Production monitoring – Databricks MLflow 3 GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring)

---

## Lifecycle Overview

```
create ──► register ──► start ──► [monitor] ──► stop ──► delete
  │            │           │                       │         │
  │            │           │                       │         │
  ▼            ▼           ▼                       ▼         ▼
Scorer()   .register()  .start()               .stop()  delete_scorer()
           name=...     sampling=...                    (by name)
           model_name=  returns NEW
                        object
```

Each transition returns a **new** scorer object. The original reference is
stale after any lifecycle method call.

---

## Step 1: Create the Scorer

### Built-in judges

```python
from mlflow.genai.scorers import (
    Safety,
    Correctness,
    Guidelines,
    RelevanceToQuery,
    ConversationCompleteness,
    UserFrustration,
)

safety = Safety()
correctness = Correctness()
guidelines = Guidelines(
    name="tone_check",
    guidelines="Responses must be professional and never condescending.",
)
relevance = RelevanceToQuery()
```

Built-in judges ship with the MLflow package and need no custom code.

### Custom @scorer functions

```python
from mlflow.genai import scorer, Score

@scorer
def sql_syntax_validator(inputs: dict, outputs: dict) -> Score:
    """Check that generated SQL parses without error."""
    import sqlglot

    sql = outputs.get("generated_sql", "")
    try:
        sqlglot.parse_one(sql, dialect="databricks")
        return Score(value=1.0, rationale="Valid SQL syntax")
    except sqlglot.errors.ParseError as e:
        return Score(value=0.0, rationale=f"Parse error: {e}")

@scorer
def response_length_guard(inputs: dict, outputs: dict) -> Score:
    """Flag excessively long responses that may indicate hallucination loops."""
    text = outputs.get("response", "")
    length = len(text)
    if length > 5000:
        return Score(value=0.0, rationale=f"Response too long: {length} chars")
    return Score(value=1.0, rationale=f"Response length OK: {length} chars")
```

---

## Step 2: Register Against a Model

Registration binds a scorer to a **model name** (the MLflow registered model
or serving endpoint name that produces traces).

```python
safety_scorer = Safety()

safety_scorer = safety_scorer.register(
    name="prod_safety_v1",
    model_name="genie-space-optimizer",
)
```

### Registration parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Unique identifier for this scorer instance |
| `model_name` | `str` | Yes | Registered model or endpoint producing traces |

### Naming conventions

Use a structured naming scheme to avoid collisions:

```python
# Environment + purpose + version
"prod_safety_v1"
"staging_correctness_v2"
"prod_domain_sql_syntax_v1"
```

---

## Step 3: Start with Sampling (CRITICAL — Immutable Pattern)

**`start()` returns a NEW scorer object.** The pre-start reference is stale.

```python
from mlflow.genai import ScorerSamplingConfig

# CORRECT: reassign the result
safety_scorer = safety_scorer.start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0)
)
```

```python
# WRONG: return value discarded — scorer may not be properly started
safety_scorer.start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0)
)
```

### ScorerSamplingConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | `float` | `1.0` | Fraction of traces to score (0.0–1.0) |

### Chaining register + start

You can chain in one expression, but **assign the final result**:

```python
safety_scorer = Safety().register(
    name="prod_safety_v1",
    model_name="genie-space-optimizer",
).start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0)
)
```

The intermediate `.register()` return value is consumed by `.start()` — only
the `.start()` result carries the active handle.

---

## Recommended Sampling Rates

| Scorer Type | Rate | Cost | Rationale |
|-------------|------|------|-----------|
| Safety (built-in) | 100% (1.0) | Medium | Every response must be policy-checked |
| Correctness (built-in) | 20% (0.2) | High | LLM judge — balance cost vs coverage |
| Guidelines (built-in) | 10% (0.1) | High | Lower priority; sampled subset suffices |
| RelevanceToQuery | 15% (0.15) | High | LLM judge for retrieval quality |
| Custom heuristic | 50–100% | Low | Regex/parse checks are cheap |
| Custom LLM judge | 5–15% | Very high | Expensive; use for spot-checks |
| ConversationCompleteness | 10% (0.1) | Very high | Multi-turn; scores full sessions |
| UserFrustration | 10% (0.1) | Very high | Multi-turn; sentiment over history |

---

## Self-Contained Scorer Requirement

Custom scorers registered for production **must be self-contained**: all
imports inside the function body. The platform serializes the function and
runs it in a worker that does not have your application's module path.

### DO — imports inside the function

```python
from mlflow.genai import scorer, Score

@scorer
def domain_quality_check(inputs: dict, outputs: dict) -> Score:
    import json
    import re
    from databricks.sdk import WorkspaceClient

    response = outputs.get("response", "")
    has_sql = bool(re.search(r"\bSELECT\b", response, re.IGNORECASE))
    return Score(
        value=1.0 if has_sql else 0.0,
        rationale="Contains SQL" if has_sql else "No SQL found",
    )
```

### DON'T — module-level imports

```python
import re  # ← will NOT be available in the worker
from my_app.utils import validate  # ← ModuleNotFoundError in production

from mlflow.genai import scorer, Score

@scorer
def broken_scorer(inputs: dict, outputs: dict) -> Score:
    return Score(value=1.0 if validate(outputs) else 0.0)
```

### Serialization constraints

| Constraint | Details |
|------------|---------|
| No module-level imports of app code | Workers lack your app's module path |
| No closures over non-serializable objects | DB connections, file handles, locks |
| No mutable global state | Each invocation may run on a different worker |
| Return type must be `Score` | Other return types cause silent failures |
| Function must be decorated with `@scorer` | Undecorated functions cannot be registered |

---

## Registering Built-in Judges

### Safety

Detects harmful, offensive, or policy-violating content.

```python
from mlflow.genai.scorers import Safety
from mlflow.genai import ScorerSamplingConfig

safety = Safety().register(
    name="prod_safety",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))
```

### Correctness

LLM-as-judge for factual accuracy against the ground truth or context.

```python
from mlflow.genai.scorers import Correctness

correctness = Correctness().register(
    name="prod_correctness",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=0.2))
```

### Guidelines

Custom rubric-based evaluation.

```python
from mlflow.genai.scorers import Guidelines

tone = Guidelines(
    name="professional_tone",
    guidelines=(
        "The response must be professional, concise, and never use "
        "slang or colloquialisms. It should directly address the "
        "user's question without unnecessary preamble."
    ),
).register(
    name="prod_tone_guidelines",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=0.1))
```

### RelevanceToQuery

Checks whether the response actually addresses the user's question.

```python
from mlflow.genai.scorers import RelevanceToQuery

relevance = RelevanceToQuery().register(
    name="prod_relevance",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=0.15))
```

---

## Multi-Turn Scorers

Conversation-aware scorers evaluate entire sessions, not individual turns.

### ConversationCompleteness

Did the agent resolve the user's request by the end of the conversation?

```python
from mlflow.genai.scorers import ConversationCompleteness
from mlflow.genai import ScorerSamplingConfig

completeness = ConversationCompleteness().register(
    name="prod_conversation_completeness",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=0.1))
```

### UserFrustration

Detects signs of user frustration (repeated questions, negative sentiment,
explicit complaints).

```python
from mlflow.genai.scorers import UserFrustration

frustration = UserFrustration().register(
    name="prod_user_frustration",
    model_name="my-agent",
).start(sampling_config=ScorerSamplingConfig(sample_rate=0.1))
```

### Multi-turn cost considerations

| Factor | Impact |
|--------|--------|
| Full conversation context sent to judge LLM | Token cost scales with conversation length |
| Typical 5-10x more expensive than single-turn | Budget accordingly |
| Use lower sample rates (5–10%) | Statistical validity at manageable cost |
| Combine with single-turn for coverage | Safety at 100%, multi-turn at 10% |

---

## Complete Example: Register 5 Production Scorers

```python
import mlflow
from mlflow.genai.scorers import Safety, Correctness, Guidelines
from mlflow.genai import ScorerSamplingConfig, scorer, Score

MODEL_NAME = "genie-space-optimizer"

# 1. Safety — score every trace
safety = Safety().register(
    name="prod_safety",
    model_name=MODEL_NAME,
)
safety = safety.start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0)
)

# 2. Correctness — 20% sample
correctness = Correctness().register(
    name="prod_correctness",
    model_name=MODEL_NAME,
)
correctness = correctness.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.2)
)

# 3. Professional tone guidelines — 10% sample
tone = Guidelines(
    name="professional_tone",
    guidelines="Be professional, concise, and helpful.",
).register(
    name="prod_tone",
    model_name=MODEL_NAME,
)
tone = tone.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.1)
)

# 4. Custom heuristic — SQL syntax check at 50%
@scorer
def sql_syntax_check(inputs: dict, outputs: dict) -> Score:
    import sqlglot
    sql = outputs.get("generated_sql", "")
    if not sql:
        return Score(value=1.0, rationale="No SQL to validate")
    try:
        sqlglot.parse_one(sql, dialect="databricks")
        return Score(value=1.0, rationale="Valid SQL")
    except Exception as e:
        return Score(value=0.0, rationale=f"Invalid SQL: {e}")

sql_check = sql_syntax_check.register(
    name="prod_sql_syntax",
    model_name=MODEL_NAME,
)
sql_check = sql_check.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.5)
)

# 5. Custom domain scorer — response completeness at 15%
@scorer
def response_completeness(inputs: dict, outputs: dict) -> Score:
    import re
    response = outputs.get("response", "")
    question = inputs.get("question", "")
    if not response.strip():
        return Score(value=0.0, rationale="Empty response")
    word_count = len(response.split())
    has_data = bool(re.search(r"\d", response))
    score = min(1.0, (word_count / 50) * 0.5 + (0.5 if has_data else 0.0))
    return Score(value=score, rationale=f"Words: {word_count}, has_data: {has_data}")

completeness = response_completeness.register(
    name="prod_response_completeness",
    model_name=MODEL_NAME,
)
completeness = completeness.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.15)
)

# Verify all scorers are active
active = mlflow.genai.list_scorers()
print(f"Active scorers: {len(active)}")
for s in active:
    print(f"  {s.name} — model: {s.model_name}")
```

---

## Scorer Management API

### list_scorers()

```python
import mlflow

scorers = mlflow.genai.list_scorers()
for s in scorers:
    print(f"{s.name}: model={s.model_name}, status={s.status}")
```

Returns all registered scorers across all models in the workspace.

### get_scorer()

```python
scorer = mlflow.genai.get_scorer("prod_safety")
print(f"Name: {scorer.name}")
print(f"Model: {scorer.model_name}")
print(f"Status: {scorer.status}")
```

Retrieve a single scorer by name for inspection or lifecycle operations.

### delete_scorer()

```python
mlflow.genai.delete_scorer("deprecated_scorer_v1")
```

Permanently removes the scorer registration. Active scoring stops immediately.
Historical scores in the trace archive are not affected.

### Lifecycle management patterns

```python
import mlflow

def rotate_scorer(old_name: str, new_scorer, new_name: str, model_name: str,
                  sample_rate: float) -> object:
    """Replace an old scorer with a new version without gaps."""
    from mlflow.genai import ScorerSamplingConfig

    new = new_scorer.register(name=new_name, model_name=model_name)
    new = new.start(sampling_config=ScorerSamplingConfig(sample_rate=sample_rate))

    try:
        mlflow.genai.delete_scorer(old_name)
    except Exception:
        pass  # old scorer may already be gone

    return new


def drain_all_scorers(model_name: str) -> None:
    """Stop and delete all scorers for a model (e.g., before decommission)."""
    scorers = mlflow.genai.list_scorers()
    for s in scorers:
        if s.model_name == model_name:
            try:
                mlflow.genai.delete_scorer(s.name)
                print(f"Deleted: {s.name}")
            except Exception as e:
                print(f"Failed to delete {s.name}: {e}")
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Scorer shows as registered but no scores appear | `start()` return value not assigned | `s = s.start(...)` |
| `ModuleNotFoundError` in scorer logs | Top-level import in custom scorer | Move all imports inside the function |
| Scores attached to wrong model | `model_name` mismatch | Verify the exact model name in MLflow UI |
| Duplicate scorer names cause confusion | Multiple scorers with same name | Namespace: `prod_safety_v2`, `staging_safety_v1` |
| High cost from LLM judges | Sample rate too high | Use sampling table; cap expensive judges at 10–20% |
| Custom scorer returns `None` | Missing `return Score(...)` | Every code path must return a `Score` |
| Backfill doesn't find scorer | Name mismatch between registration and backfill call | Use exact `name` from `list_scorers()` |

---

## References

- [Production monitoring docs](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring)
- [MLflow GenAI scorers API](https://mlflow.org/docs/latest/genai/scorers/)
- [`src/genie_space_optimizer/common/config.py`](../../../../src/genie_space_optimizer/common/config.py) — `MLFLOW_THRESHOLDS`, `MODEL_NAME_TEMPLATE`

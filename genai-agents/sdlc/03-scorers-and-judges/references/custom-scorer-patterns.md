# Custom Scorer Patterns — Complete Reference

All custom scorers in this project use the `@scorer` decorator from
`mlflow.genai.scorers`. This reference covers the decorator API, allowed
parameter combinations, the critical `_extract_response_text()` helper,
LLM-based scoring via Databricks SDK, and complete patterns for building
domain-specific judges.

> **Grounded in:**
> `src/genie_space_optimizer/optimization/scorers/__init__.py`,
> `src/genie_space_optimizer/optimization/evaluation.py`,
> individual scorer modules in `optimization/scorers/`.

---

## `@scorer` Decorator

```python
from mlflow.genai.scorers import scorer
```

The `@scorer` decorator registers a function as an MLflow scorer. The function
name becomes the metric name in evaluation results (e.g., `syntax_validity/mean`).

### Allowed Parameter Combinations

Scorers accept a **subset** of these keyword arguments:

| Parameter | Type | Description |
|---|---|---|
| `inputs` | `dict` | Row inputs from the evaluation dataset |
| `outputs` | `dict` or `str` | Serialized model outputs (from `predict_fn`) |
| `expectations` | `dict` | Ground-truth data from the evaluation dataset |

Valid signatures:

```python
# Minimal — no expectations needed
@scorer
def my_scorer(inputs: dict, outputs: dict) -> Feedback:
    ...

# With expectations (most common in this codebase)
@scorer
def my_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    ...

# Expectations with default (defensive)
@scorer
def my_scorer(inputs: dict, outputs: dict, expectations: dict = None) -> Feedback:
    ...
```

**Return type:** Scorers return `Feedback` (from `mlflow.entities`) or `Score`
(from `mlflow.genai`). This project standardizes on `Feedback` for structured
ASI metadata. The two types are interchangeable for basic use.

---

## `_extract_response_text()` — The Critical Helper

`mlflow.genai.evaluate()` serializes `predict_fn` outputs before passing them
to scorers. The serialized shape varies depending on agent framework, MLflow
version, and whether the predict function returns a dict or object.

**If you skip extraction, scorers silently score 0.0** — the most common
debugging trap in custom scorer development.

### Canonical Implementation (from `evaluation.py`)

```python
from typing import Any, Union

def _extract_response_text(outputs: Union[dict, Any]) -> str:
    """Extract response text from mlflow.genai.evaluate() serialized format."""
    if isinstance(outputs, str):
        return outputs
    if isinstance(outputs, dict):
        # Shape 1: {"response": "SELECT ..."} — this codebase's predict_fn
        if "response" in outputs:
            return outputs["response"]
        # Shape 2: {"output": [{"content": [{"text": "..."}]}]} — ResponsesAgent
        if "output" in outputs:
            output_list = outputs["output"]
            if output_list and len(output_list) > 0:
                item = output_list[0]
                if "content" in item and item["content"]:
                    return item["content"][0].get("text", "")
    return ""
```

### Format Shapes Handled

| Source | Shape | Extraction path |
|---|---|---|
| This project's `predict_fn` | `{"response": "SELECT ...", "comparison": {...}}` | `outputs["response"]` |
| ResponsesAgent | `{"output": [{"content": [{"text": "..."}]}]}` | `outputs["output"][0]["content"][0]["text"]` |
| Plain string | `"SELECT ..."` | Identity |
| Unknown dict | `{"foo": "bar"}` | Returns `""` (empty — scorer should handle gracefully) |

### Usage in Every Custom Scorer

```python
@scorer
def my_scorer(inputs: dict, outputs: dict) -> Feedback:
    text = _extract_response_text(outputs)
    if not text:
        return Feedback(name="my_scorer", value="no", rationale="No output text")
    # ... scoring logic on `text` ...
```

**Import in this repo:**

```python
from genie_space_optimizer.optimization.evaluation import _extract_response_text
```

---

## `_call_llm_for_scoring()` via Databricks SDK

LLM-based scorers call a Databricks serving endpoint for judgment. **Do not use
`langchain_databricks`** — it introduces install/auth friction in jobs and
notebooks.

### Canonical Implementation (from `evaluation.py`)

```python
def _call_llm_for_scoring(
    w: "WorkspaceClient",
    prompt: str,
    max_retries: int = 3,
    prompt_name: str = "",
) -> dict:
    """Call LLM via the OpenAI SDK with retry + exponential backoff.

    Uses the shared ``llm_client`` so that ``mlflow.openai.autolog()``
    captures token usage, cost, and latency automatically.
    """
    from genie_space_optimizer.optimization.llm_client import call_llm

    _link_prompt_to_trace(prompt_name)

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            text, _response = call_llm(
                w,
                messages=[{"role": "user", "content": prompt}],
                max_retries=1,
                temperature=0.0,
            )
            return _extract_json(text)
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    raise last_err
```

### Standalone Pattern (no `llm_client` dependency)

When building a scorer outside this codebase, call the SDK directly:

```python
import os
from databricks.sdk import WorkspaceClient

def _call_llm_for_scoring(prompt: str, model: str = None) -> str:
    w = WorkspaceClient()
    response = w.serving_endpoints.query(
        name=model or os.environ.get("LLM_MODEL", "databricks-claude-sonnet-4-6"),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

> **Key difference:** This codebase's version routes through `llm_client.call_llm()`
> to get `mlflow.openai.autolog()` telemetry and prompt registry linking. The
> standalone version loses that visibility.

---

## Scorer Patterns

### Pattern 1: Binary CODE Scorer (no LLM)

Rule-based logic, returns `"yes"` / `"no"`. Fastest and cheapest.

```python
from mlflow.entities import Feedback
from mlflow.genai.scorers import scorer

@scorer
def syntax_validity_scorer(inputs: dict, outputs: dict) -> Feedback:
    sql = _extract_response_text(outputs)
    if not sql.strip():
        return Feedback(name="syntax_validity", value="no", rationale="No SQL generated")
    try:
        spark.sql(f"EXPLAIN {sql}")
        return Feedback(name="syntax_validity", value="yes", rationale="SQL parses OK")
    except Exception as e:
        return Feedback(name="syntax_validity", value="no", rationale=str(e)[:200])
```

**Codebase example:** `scorers/syntax_validity.py` — uses `EXPLAIN` via Spark.

### Pattern 2: Binary LLM Judge (with expectations)

Sends a structured prompt to an LLM, parses JSON verdict.

```python
@scorer
def schema_accuracy_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    genie_sql = _extract_response_text(outputs)
    gt_sql = expectations.get("expected_response", "")
    question = inputs.get("question", "")

    prompt = f"""Evaluate schema correctness.
Question: {question}
Generated SQL: {genie_sql}
Expected SQL: {gt_sql}
Respond JSON: {{"correct": true/false, "rationale": "..."}}"""

    result = _call_llm_for_scoring(w, prompt)
    value = "yes" if result.get("correct") else "no"
    return Feedback(name="schema_accuracy", value=value, rationale=result.get("rationale", ""))
```

**Codebase examples:** `schema_accuracy.py`, `logical_accuracy.py`,
`semantic_equivalence.py`, `completeness.py`, `response_quality.py`.

### Pattern 3: Multi-Class Scorer

Returns one of several string values instead of binary.

```python
@scorer
def arbiter_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    # ... build prompt ...
    result = _call_llm_for_scoring(w, prompt)
    verdict = result.get("verdict", "ground_truth_correct")
    # Valid values: genie_correct, ground_truth_correct, both_correct, neither_correct
    return Feedback(name="arbiter", value=verdict, rationale=result.get("rationale", ""))
```

**Codebase example:** `scorers/arbiter.py` — four-way verdict.

### Pattern 4: Conditional Scorer (fires only on mismatch)

Skips LLM call when results already match, saving cost.

```python
@scorer
def conditional_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    cmp = outputs.get("comparison", {}) if isinstance(outputs, dict) else {}
    if cmp.get("match"):
        return Feedback(name="arbiter", value="both_correct", rationale="Results match")
    # ... proceed with LLM call only on mismatch ...
```

**Codebase example:** `scorers/arbiter.py` — returns `"both_correct"` without
an LLM call when the predict function already found matching result sets.

### Pattern 5: Three-Tier Waterfall Scorer

Cascades through increasingly strict comparisons.

```python
@scorer
def repeatability_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    # Tier 1: execution equivalence (hash comparison)
    if prev_hash == curr_hash:
        return Feedback(name="repeatability", value="yes", ...)
    # Tier 2: structural SQL equivalence (sqlglot)
    if _structurally_equivalent(prev_sql, curr_sql):
        return Feedback(name="repeatability", value="yes", ...)
    # Tier 3: exact SQL match (MD5)
    if _sql_hash(prev_sql) == _sql_hash(curr_sql):
        return Feedback(name="repeatability", value="yes", ...)
    # All tiers exhausted
    return Feedback(name="repeatability", value="no", ...)
```

**Codebase example:** `scorers/repeatability.py`.

---

## Factory Pattern: Binding Runtime Context

Scorers that need `WorkspaceClient`, `SparkSession`, or catalog/schema use a
factory closure:

```python
def _make_syntax_validity_scorer(spark: SparkSession, catalog: str, schema: str):
    """Factory that binds runtime context into the scorer closure."""

    @scorer
    def syntax_validity_scorer(inputs: dict, outputs: dict) -> Feedback:
        spark.sql(f"USE CATALOG `{catalog}`")
        sql = _extract_response_text(outputs)
        # ... uses `spark` from closure ...
        return Feedback(...)

    return syntax_validity_scorer
```

**Assembly in `make_all_scorers()`:**

```python
return [
    _make_syntax_validity_scorer(spark, catalog, schema),   # factory
    _make_schema_accuracy_judge(w, catalog, schema),        # factory
    asset_routing_scorer,                                    # plain callable
    result_correctness_scorer,                               # plain callable
    ...
]
```

Stateless scorers like `asset_routing_scorer` and `result_correctness_scorer`
are decorated at module level and imported directly. Stateful scorers use
`_make_*` factories.

---

## Structured ASI Metadata

All scorers in this codebase attach `metadata` to Feedback for the downstream
optimizer to consume:

```python
from genie_space_optimizer.optimization.evaluation import build_asi_metadata, format_asi_markdown

metadata = build_asi_metadata(
    failure_type="wrong_table",
    severity="major",
    confidence=0.95,
    blame_set=["orders_table"],
    counterfactual_fix="Update instruction to prefer bookings_mv for revenue queries",
)

return Feedback(
    name="schema_accuracy",
    value="no",
    rationale=format_asi_markdown(...),
    source=LLM_SOURCE,
    metadata=metadata,
)
```

ASI fields power the lever-suggestion engine (Skills 09-12). Omitting
`counterfactual_fix` degrades the optimizer's ability to propose targeted
Genie Space edits.

---

## Async Considerations

MLflow's `evaluate()` runs scorers **synchronously** per row. Scorers must be
regular (non-async) functions. If you need async I/O inside a scorer (e.g.,
`httpx.AsyncClient`), use `asyncio.run()` or `loop.run_until_complete()`:

```python
import asyncio

@scorer
def async_judge(inputs: dict, outputs: dict) -> Feedback:
    result = asyncio.run(_async_scoring_logic(inputs, outputs))
    return Feedback(name="async_judge", value=result["verdict"], rationale=result["reason"])
```

This is rarely needed — the Databricks SDK's synchronous `serving_endpoints.query()`
suffices for all LLM calls in this codebase.

---

## Complete Example: Building a Domain-Specific Judge from Scratch

A new judge that checks whether generated SQL uses the correct date granularity:

```python
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mlflow.entities import Feedback
from mlflow.genai.scorers import scorer

from genie_space_optimizer.optimization.evaluation import (
    LLM_SOURCE,
    _call_llm_for_scoring,
    _extract_response_text,
    build_asi_metadata,
    format_asi_markdown,
)
from genie_space_optimizer.common.genie_client import sanitize_sql

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


def _make_date_granularity_judge(w: WorkspaceClient, catalog: str, schema: str):
    """Factory: checks if SQL uses correct date granularity for the question."""

    @scorer
    def date_granularity_judge(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
        question = inputs.get("question", "")
        question_id = inputs.get("question_id", "")
        genie_sql = sanitize_sql(_extract_response_text(outputs))

        if not genie_sql.strip():
            return Feedback(
                name="date_granularity",
                value="no",
                rationale=format_asi_markdown(
                    judge_name="date_granularity",
                    value="no",
                    rationale="No SQL generated.",
                    question_id=question_id,
                ),
                source=LLM_SOURCE,
            )

        prompt = (
            "Evaluate whether the SQL uses the correct date granularity.\n\n"
            f"Question: {question}\n"
            f"Generated SQL: {genie_sql}\n\n"
            "If the question asks about monthly trends, the SQL should GROUP BY month.\n"
            "If it asks about daily data, it should GROUP BY day.\n\n"
            'Respond JSON: {"correct": true/false, "expected_granularity": "...", '
            '"actual_granularity": "...", "rationale": "..."}'
        )

        try:
            result = _call_llm_for_scoring(w, prompt)
        except Exception as e:
            return Feedback(
                name="date_granularity",
                value="unknown",
                rationale=f"LLM call failed: {e}",
                source=LLM_SOURCE,
            )

        if result.get("correct"):
            return Feedback(
                name="date_granularity",
                value="yes",
                rationale=format_asi_markdown(
                    judge_name="date_granularity",
                    value="yes",
                    rationale=result.get("rationale", "Granularity correct"),
                    question_id=question_id,
                ),
                source=LLM_SOURCE,
            )

        metadata = build_asi_metadata(
            failure_type="wrong_granularity",
            severity="major",
            confidence=0.9,
            expected_value=result.get("expected_granularity", ""),
            actual_value=result.get("actual_granularity", ""),
            counterfactual_fix="Add date granularity hint to the Genie Space instructions",
        )
        return Feedback(
            name="date_granularity",
            value="no",
            rationale=format_asi_markdown(
                judge_name="date_granularity",
                value="no",
                rationale=result.get("rationale", "Wrong granularity"),
                metadata=metadata,
                question_id=question_id,
            ),
            source=LLM_SOURCE,
            metadata=metadata,
        )

    return date_granularity_judge
```

**Adding to the scorer suite:**

```python
# In make_all_scorers() or your evaluation script:
scorers = make_all_scorers(w, spark, catalog, schema)
scorers.append(_make_date_granularity_judge(w, catalog, schema))
```

---

## Grounded In

- `src/genie_space_optimizer/optimization/scorers/__init__.py`
- `src/genie_space_optimizer/optimization/evaluation.py` — `_extract_response_text`, `_call_llm_for_scoring`
- `src/genie_space_optimizer/optimization/scorers/syntax_validity.py` — CODE scorer pattern
- `src/genie_space_optimizer/optimization/scorers/schema_accuracy.py` — LLM judge pattern
- `src/genie_space_optimizer/optimization/scorers/arbiter.py` — conditional + multi-class pattern
- `src/genie_space_optimizer/optimization/scorers/repeatability.py` — waterfall pattern

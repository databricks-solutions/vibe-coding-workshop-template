# `make_judge` Template Constraints — Complete Reference

`make_judge()` from `mlflow.genai.scorers` creates an LLM scorer from a prompt
template. It is a lightweight alternative to the `@scorer` decorator when you
only need the LLM to render a judgment from a simple template — no custom
extraction logic, no Spark calls, no structured metadata.

This reference covers the strict template variable constraints, full usage
examples, common errors, and when to choose `make_judge()` vs `@scorer`.

> **Grounded in:**
> `mlflow.genai.scorers.make_judge` API,
> MLflow template validation internals,
> `src/genie_space_optimizer/optimization/evaluation.py`.

---

## Template Variable Constraints

`make_judge()` templates use Jinja2-style `{{ variable }}` placeholders. MLflow
validates the template at construction time and **only allows five variables**:

| Variable | Type at runtime | Source |
|---|---|---|
| `inputs` | `dict` | Row inputs from the evaluation dataset |
| `outputs` | serialized model output | Return value of `predict_fn` (may be dict or string) |
| `trace` | MLflow Trace object | The trace from the predict call |
| `expectations` | `dict` | Ground-truth data from the evaluation dataset |
| `conversation` | list of messages | Multi-turn conversation transcript |

Any other variable name in the template raises an `MlflowException` at scorer
construction (not at evaluation time — the error is immediate).

### Valid Template

```python
from mlflow.genai.scorers import make_judge

domain_judge = make_judge(
    name="domain_accuracy",
    judge_prompt="""
You are evaluating a response for domain accuracy.

Question: {{ inputs.question }}
Response: {{ outputs }}
Expected: {{ expectations.expected_answer }}

Score 1 if the response is accurate, 0 if not.
""",
)
```

### Accessing Nested Fields

Use dot notation to access dict fields:

```python
judge_prompt="""
User asked: {{ inputs.question }}
Question ID: {{ inputs.question_id }}
Expected SQL: {{ expectations.expected_response }}
"""
```

Dot access works because MLflow passes the dicts as Jinja2 context objects.
If a key contains special characters, use bracket notation:
`{{ inputs["question-text"] }}`.

---

## Common Errors

### Error 1: Custom Variable Name

```python
# WRONG — "response" is not an allowed variable
make_judge(
    name="my_judge",
    judge_prompt="Evaluate: {{ response }}",  # MlflowException!
)
```

**Fix:** Use `{{ outputs }}` instead of `{{ response }}`.

### Error 2: No Variables at All

```python
# WRONG — template must contain at least one variable
make_judge(
    name="my_judge",
    judge_prompt="Is this response good?",  # MlflowException!
)
```

**Fix:** Include at least one template variable:
```python
judge_prompt="Is this response good? {{ outputs }}"
```

### Error 3: Python f-string Variables

```python
# WRONG — Python f-strings are not Jinja2 templates
question = "What is revenue?"
make_judge(
    name="my_judge",
    judge_prompt=f"Question: {question}\nResponse: {{{{ outputs }}}}",
)
```

**Fix:** Do not mix Python f-strings with Jinja2 templates. Use only Jinja2:
```python
judge_prompt="Question: {{ inputs.question }}\nResponse: {{ outputs }}"
```

### Error 4: Using `trace` Without Tracing Enabled

```python
make_judge(
    name="my_judge",
    judge_prompt="Trace: {{ trace }}\nOutput: {{ outputs }}",
)
```

This constructs successfully but may fail at evaluation time if tracing is
disabled. The `trace` variable will be `None`, and Jinja2 will render it as
the string `"None"`.

### Error 5: Expecting `outputs` to Be a String

```python
judge_prompt="""
The response starts with: {{ outputs[:50] }}
"""
```

**Fix:** `outputs` may be a dict (serialized agent output). Do not slice it.
Access fields explicitly: `{{ outputs.response }}` or handle in the prompt
text by instructing the LLM to parse the output.

---

## `judge_prompt` vs `instructions` Keyword

The keyword for the template string may differ by MLflow version:

| MLflow Version | Keyword |
|---|---|
| Early MLflow 3.x | `instructions` |
| Later MLflow 3.x | `judge_prompt` |

Check your version: `mlflow.version.VERSION`. If `judge_prompt` raises a
`TypeError`, try `instructions` instead. The allowed template variables are
unchanged across versions.

---

## Full Example: make_judge with All Five Variables

```python
from mlflow.genai.scorers import make_judge

comprehensive_judge = make_judge(
    name="comprehensive_check",
    judge_prompt="""
You are evaluating an AI agent's response.

## Inputs
User question: {{ inputs.question }}
Question category: {{ inputs.category }}

## Agent Output
{{ outputs }}

## Expected Answer
{{ expectations.expected_response }}

## Conversation Context
{% if conversation %}
Previous turns:
{% for msg in conversation %}
- {{ msg.role }}: {{ msg.content }}
{% endfor %}
{% endif %}

## Trace Information
{% if trace %}
Trace ID: {{ trace.info.trace_id }}
{% endif %}

Evaluate whether the response correctly answers the question.
Respond with a score of 1 (correct) or 0 (incorrect) and a brief rationale.
""",
)
```

> **Note:** `conversation` and `trace` may not be populated for all evaluation
> dataset rows. Use Jinja2 `{% if %}` guards to handle `None` gracefully.

---

## Comparison: `make_judge()` vs `@scorer` Decorator

| Capability | `make_judge()` | `@scorer` decorator |
|---|---|---|
| Custom extraction logic | No — receives raw `outputs` | Yes — call `_extract_response_text()` |
| Structured metadata (ASI) | No — returns basic Score | Yes — return `Feedback` with `metadata` |
| SQL execution (Spark) | No | Yes — bind via factory closure |
| Conditional logic (skip rows) | No — always calls LLM | Yes — early return without LLM call |
| Multi-class verdicts | No — numeric or binary only | Yes — return any string value |
| Prompt registry linking | No | Yes — call `_link_prompt_to_trace()` |
| Ease of use | Higher — just write a template | Lower — write a full function |
| LLM cost control | One call per row (always) | Zero calls for skipped rows |

### When to Use `make_judge()`

- Quick prototyping of new quality dimensions
- Simple "does this response follow X?" checks
- Adding a lightweight guideline scorer without writing a full module
- Supplemental scoring on top of the custom 9-judge suite

### When to Use `@scorer`

- You need `_extract_response_text()` to handle output format variations
- You need structured ASI metadata for the optimizer to consume
- The scorer should skip rows conditionally (save LLM cost)
- You need runtime context (Spark, WorkspaceClient, catalog/schema)
- The verdict has more than two values (multi-class)

### Practical Recommendation

**This codebase uses `@scorer` for all 9 production judges.** `make_judge()`
is useful for one-off experiments or supplemental checks but lacks the
structured output the optimizer pipeline requires.

---

## Nesting Extra Fields

If you need data beyond `inputs`, `outputs`, `expectations`, `trace`, and
`conversation` — nest it:

```python
# In the evaluation dataset:
eval_df["inputs"] = eval_df.apply(
    lambda row: {
        "question": row["question"],
        "question_id": row["question_id"],
        "category": row["category"],         # extra field
        "space_id": row["space_id"],          # extra field
    },
    axis=1,
)
```

Then access via `{{ inputs.category }}` and `{{ inputs.space_id }}` in the
template. Do not invent new top-level template variables.

---

## `make_judge` Result Is Not Standalone

The object returned by `make_judge()` is a scorer, not an evaluator. You
cannot call `.evaluate()` on it. Pass it in the `scorers` list:

```python
# WRONG
judge = make_judge(name="my_judge", judge_prompt="...")
result = judge.evaluate(data)  # AttributeError!

# CORRECT
import mlflow
result = mlflow.genai.evaluate(
    data=eval_df,
    predict_fn=predict_fn,
    scorers=[judge],
)
```

---

## Grounded In

- `mlflow.genai.scorers.make_judge` — MLflow 3.x API
- `src/genie_space_optimizer/optimization/evaluation.py` — `_extract_response_text`, factory patterns
- [Databricks MLflow 3 GenAI: Scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)
- [MLflow GenAI Evaluate](https://mlflow.org/docs/latest/llms/llm-evaluate/)

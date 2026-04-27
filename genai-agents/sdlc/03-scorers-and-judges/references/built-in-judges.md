# Built-in MLflow Judges — Complete Reference

MLflow ships first-party scorers for common quality dimensions. All are imported
from `mlflow.genai.scorers`. This reference covers each judge, its scoring
behaviour, when to use it, and how to compose them in a scorer list.

> **Version note:** Exact exports depend on your MLflow version. Run
> `from mlflow.genai import scorers; dir(scorers)` to confirm availability.

---

## Judge Catalogue

### Safety

```python
from mlflow.genai.scorers import Safety

safety = Safety()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"safe"` / `"unsafe"` |
| MLflow metric key | `safety/mean` |
| Requires expectations | No |

**What it checks:** Whether the response contains harmful, dangerous, or
inappropriate content. Covers hate speech, violence instructions, PII leakage,
self-harm encouragement, and regulated advice.

**When to use:** Always include in any customer-facing agent. Low overhead,
high signal for compliance.

**Example output:**

```json
{"name": "safety", "value": "safe", "rationale": "Response provides factual SQL output with no harmful content."}
```

---

### Correctness

```python
from mlflow.genai.scorers import Correctness

correctness = Correctness()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"correct"` / `"incorrect"` |
| MLflow metric key | `correctness/mean` |
| Requires expectations | Yes (`expected_response` or `expected_facts`) |

**What it checks:** Whether the response is factually correct relative to the
expected answer. The judge compares semantic meaning, not exact string match.

**When to use:** When you have ground-truth answers. In this codebase, the
custom `result_correctness_scorer` (CODE-based) and the LLM judges
(`schema_accuracy`, `logical_accuracy`, etc.) supersede `Correctness` for SQL
evaluation. Use `Correctness` for general NL-answer agents.

**Example output:**

```json
{"name": "correctness", "value": "correct", "rationale": "Response matches expected answer on all key facts."}
```

---

### RelevanceToQuery

```python
from mlflow.genai.scorers import RelevanceToQuery

relevance = RelevanceToQuery()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"relevant"` / `"irrelevant"` |
| MLflow metric key | `relevance_to_query/mean` |
| Requires expectations | No |

**What it checks:** Whether the response addresses the user's question rather
than providing off-topic information.

**When to use:** Useful for chat-based agents where the model may hallucinate or
drift. Less critical for SQL-only Genie evaluation (the completeness judge
handles the same intent).

> **Alias warning:** Older MLflow versions logged this as `relevance/mean`.
> See `METRIC_ALIASES` in the SKILL for cross-version compatibility.

**Example output:**

```json
{"name": "relevance_to_query", "value": "relevant", "rationale": "Response directly answers the user's question about revenue by region."}
```

---

### RetrievalGroundedness

```python
from mlflow.genai.scorers import RetrievalGroundedness

grounded = RetrievalGroundedness()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"grounded"` / `"ungrounded"` |
| MLflow metric key | `retrieval_groundedness/mean` |
| Requires expectations | No (uses trace retrieval spans) |

**What it checks:** Whether the response is grounded in retrieved context rather
than fabricated. Inspects `RETRIEVAL`-type spans in the MLflow trace.

**When to use:** RAG pipelines where retrieved documents feed the answer. Not
applicable to the Genie SQL pipeline (no retrieval spans), but valuable if you
add a documentation-retrieval step.

**Example output:**

```json
{"name": "retrieval_groundedness", "value": "grounded", "rationale": "All claims in the response can be traced to retrieved documents."}
```

---

### Guidelines

```python
from mlflow.genai.scorers import Guidelines

guidelines = Guidelines(
    guidelines=[
        "Include time context in all date-related queries",
        "Format monetary values as USD with two decimal places",
        "Cite the source table for all data references",
        "Never expose raw column names to the user",
    ]
)
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"adherent"` / `"non-adherent"` |
| MLflow metric key | `guidelines/mean` |
| Requires expectations | No |

**What it checks:** Whether the response follows every guideline in the list.
The judge evaluates all criteria jointly; a single violation fails the row.

**When to use:** Enforce domain-specific style and business rules. The
judge scales with list length but accuracy degrades above ~6 criteria —
the LLM starts conflating or ignoring items.

**Guideline count sweet spot:** 4 to 6 focused criteria. If you have more,
split into multiple `Guidelines(name=..., guidelines=[...])` instances with
distinct names.

**Example output:**

```json
{"name": "guidelines", "value": "non-adherent", "rationale": "Response uses raw column name 'booking_created_date' instead of a user-friendly label."}
```

---

### ConversationCompleteness

```python
from mlflow.genai.scorers import ConversationCompleteness

conv_complete = ConversationCompleteness()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"complete"` / `"incomplete"` |
| MLflow metric key | `conversation_completeness/mean` |
| Requires expectations | No (uses conversation field) |

**What it checks:** Whether the agent addressed every part of a multi-turn user
goal. Examines the full conversation transcript, not just the last turn.

**When to use:** Multi-turn chat agents where the user asks follow-up questions.
For single-turn SQL benchmarks in this codebase, the custom `completeness`
judge is preferred (it compares SQL against the question directly).

---

### UserFrustration

```python
from mlflow.genai.scorers import UserFrustration

frustration = UserFrustration()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"frustrated"` / `"not_frustrated"` |
| MLflow metric key | `user_frustration/mean` |
| Requires expectations | No (uses conversation field) |

**What it checks:** Signals such as user repetition, escalation language,
unresolved loops, and explicit dissatisfaction across the conversation.

**When to use:** Chat-based agents deployed in production where you want to
monitor user experience. A rising frustration score signals instruction or
capability gaps.

---

### ConversationalSafety

```python
from mlflow.genai.scorers import ConversationalSafety

conv_safety = ConversationalSafety()
```

| Property | Value |
|---|---|
| Type | LLM-based |
| Scale | Binary — `"safe"` / `"unsafe"` |
| MLflow metric key | `conversational_safety/mean` |
| Requires expectations | No (uses conversation field) |

**What it checks:** Safety with full conversational context — not just the last
assistant message. Detects jailbreak escalation, progressive boundary pushing,
and context-dependent harmful content that single-turn `Safety` may miss.

**When to use:** Multi-turn agents where safety risk increases with conversation
length. Use alongside `Safety()` (single-turn) for comprehensive coverage.

> **Availability:** May not be present in all MLflow versions. Check
> `hasattr(mlflow.genai.scorers, 'ConversationalSafety')` before importing.

---

## Composing Multiple Judges

Pass a list to `mlflow.genai.evaluate(scorers=...)`. Mixing built-in and custom
scorers works seamlessly:

```python
import mlflow
from mlflow.genai.scorers import Safety, Guidelines

from genie_space_optimizer.optimization.scorers import make_all_scorers

custom_scorers = make_all_scorers(w, spark, catalog, schema)

all_scorers = custom_scorers + [
    Safety(),
    Guidelines(guidelines=["Always include the currency symbol"]),
]

result = mlflow.genai.evaluate(
    data=eval_df,
    predict_fn=predict_fn,
    scorers=all_scorers,
)
```

Order in the list does not affect results — each scorer runs independently.
However, order determines the column order in the evaluation results DataFrame.

---

## Performance Characteristics

| Judge | Type | Latency | Cost | Parallelizable |
|---|---|---|---|---|
| Safety | LLM-based | ~1-3s per row | Token cost | Yes |
| Correctness | LLM-based | ~1-3s per row | Token cost | Yes |
| RelevanceToQuery | LLM-based | ~1-3s per row | Token cost | Yes |
| RetrievalGroundedness | LLM-based | ~2-4s per row | Token cost | Yes |
| Guidelines | LLM-based | ~2-5s per row | Token cost (scales with guideline count) | Yes |
| ConversationCompleteness | LLM-based | ~2-5s per row | Token cost (scales with conversation length) | Yes |
| UserFrustration | LLM-based | ~1-3s per row | Token cost | Yes |
| ConversationalSafety | LLM-based | ~2-5s per row | Token cost (scales with conversation length) | Yes |

All built-in judges are LLM-based. MLflow dispatches them to the configured
model endpoint. For high-throughput evaluation, the framework parallelizes
scorer invocations across rows automatically.

**Cost control:** Built-in judges share the same model endpoint configured in
MLflow. Each row incurs one LLM call per judge. For a 50-row benchmark with 3
built-in judges + 9 custom judges, budget ~600 LLM calls total.

---

## Codebase Integration Notes

This project's primary evaluation uses 9 custom scorers assembled by
`make_all_scorers()` rather than the built-in judges. The custom judges are
purpose-built for SQL comparison and include features the built-ins lack:

- Result-set comparison with hash-based matching
- SQL EXPLAIN validation via Spark
- Arbiter re-adjudication when results disagree
- Structured ASI (Actionable Scorer Information) metadata for the optimizer

Built-in judges complement the custom suite when you need:
- `Safety()` — compliance gating before production deployment
- `Guidelines()` — enforcing Genie Space-specific style rules
- Conversation judges — evaluating multi-turn chat interactions

To add built-ins, append them to the list returned by `make_all_scorers()`:

```python
scorers = make_all_scorers(w, spark, catalog, schema)
scorers.append(Safety())
```

---

## Grounded In

- `mlflow.genai.scorers` module (MLflow 3.x)
- `src/genie_space_optimizer/optimization/scorers/__init__.py` — `make_all_scorers()` assembly
- [Databricks MLflow 3 GenAI: Scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)

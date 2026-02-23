---
name: mlflow-genai-evaluation
description: >
  MLflow 3 GenAI evaluation patterns with LLM judges, MemAlign judge alignment, GEPA prompt
  optimization, custom scorers with _extract_response_text() helper, Databricks SDK for scorer
  LLM calls, metric aliases, threshold checking, 4-6 guidelines best practice, foundation model
  endpoints. Use when implementing agent evaluation pipelines, creating custom LLM judges,
  aligning judges with domain feedback, optimizing prompts, setting up UC trace ingestion for
  production monitoring, or troubleshooting evaluation errors.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.2.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-tools-core/databricks_tools_core/sql/sql.py"
      relationship: "reference"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-mlflow-evaluation/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "latest"
---

# MLflow GenAI Evaluation Patterns

Production-grade patterns for evaluating Databricks GenAI agents using MLflow 3.0+ `mlflow.genai.evaluate()` with LLM-as-judge scorers and custom evaluation metrics.

## When to Use

- Implementing agent evaluation pipelines with LLM judges
- Creating custom domain-specific evaluation scorers
- Setting up evaluation datasets for agent testing
- Checking deployment thresholds before production deployment
- Troubleshooting evaluation errors (0.0 scores, metric name mismatches)
- Optimizing guidelines for better evaluation scores
- Querying evaluation results programmatically
- Aligning LLM judges with domain expert feedback via MemAlign
- Automated prompt optimization with GEPA (`optimize_prompts()`)
- Setting up Unity Catalog trace ingestion for production monitoring

---

## Upstream API Note

The upstream `databricks-mlflow-evaluation` skill in AI-Dev-Kit covers 8 end-to-end workflows: first-time evaluation setup, production trace-to-dataset, performance optimization, regression detection, custom scorer development, UC trace ingestion and production monitoring, judge alignment with MemAlign, and automated prompt optimization with GEPA.

**Critical API facts:**
- Use `mlflow.genai.evaluate()` (NOT `mlflow.evaluate()`)
- Data format: `{"inputs": {"query": "..."}}` (nested structure required)
- MemAlign is scorer-agnostic (works with any `feedback_value_type`)
- GEPA optimization dataset must have both `inputs` AND `expectations` per record
- Requires MLflow >= 3.5.0 for `optimize_prompts()`

---

## ⚠️ CRITICAL: Response Extraction Helper

**MANDATORY: `_extract_response_text()` must be included in ALL custom scorers.**

`mlflow.genai.evaluate()` serializes `ResponsesAgentResponse` to a dict before passing to scorers. Without proper extraction, scorers receive serialized dicts and return 0.0 scores (silent failure).

**Full implementation:** See `scripts/evaluation_helpers.py` for complete function code.

**Why this matters:**
- ❌ Without helper: 9+ custom scorers return 0.0 for ALL responses
- ❌ Silent failure - no error messages, just 0.0 scores
- ❌ Took 5+ deployment iterations to discover root cause
- ✅ With helper: Scorers work correctly first time

---

## ⚠️ CRITICAL: Databricks SDK for LLM Calls

**ALWAYS use Databricks SDK (NOT `langchain_databricks`) for LLM calls in custom scorers.**

| Issue | langchain_databricks | Databricks SDK |
|---|---|---|
| **Serverless Compute** | ❌ Package install failures | ✅ No install needed |
| **Authentication** | ❌ Varies by environment | ✅ Automatic in notebooks |
| **Deployment Jobs** | ❌ Unreliable auth | ✅ Reliable auth |
| **Support** | ⚠️ Community package | ✅ Official Databricks SDK |

**Full implementation:** See `scripts/evaluation_helpers.py` for `_call_llm_for_scoring()` helper.

---

## Guidelines Best Practice: 4-6 Sections

**CRITICAL: Keep guidelines to 4-6 essential sections (NOT 8+).**

### ❌ DON'T: Too Many Guidelines Sections

```python
# BAD: 8 comprehensive guidelines = low scores
guidelines = [
    "Section 1: Response Structure (200 words)",
    "Section 2: Data Accuracy (150 words)",
    "Section 3: No Fabrication (180 words)",
    "Section 4: Actionability (160 words)",
    "Section 5: Domain Expertise (200 words)",
    "Section 6: Cross-Domain Intelligence (150 words)",
    "Section 7: Professional Tone (120 words)",
    "Section 8: Completeness (170 words)",
]

# Result: guidelines/mean = 0.20 (too strict!)
```

### ✅ DO: 4-6 Essential Guidelines

```python
# GOOD: 4 focused, critical guidelines = higher, more meaningful scores
guidelines = [
    """Data Accuracy and Specificity:
    - MUST include specific numbers (costs, DBUs, percentages)
    - MUST include time context (when data is from)
    - MUST include trend direction (increased/decreased)""",
    
    """No Data Fabrication (CRITICAL):
    - MUST NEVER fabricate numbers
    - If Genie errors, MUST state explicitly""",
    
    """Actionability and Recommendations:
    - MUST provide specific, actionable next steps
    - MUST include concrete implementation details""",
    
    """Professional Enterprise Tone:
    - MUST maintain professional tone
    - MUST use proper formatting (markdown, tables)""",
]

# Result: guidelines/mean = 0.5+ (achievable, meaningful)
```

**Why this matters:**
- 8+ sections = overly strict scoring (0.20 average)
- 4-6 sections = achievable, meaningful scores (0.50+ average)
- Focus on critical quality dimensions only

---

## Run Naming Convention

**ALWAYS use consistent run naming** for querying latest evaluation results.

```python
# ✅ CORRECT: Consistent prefix + timestamp
from datetime import datetime

run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

mlflow.genai.evaluate(
    model=model_uri,
    data=eval_dataset,
    model_type="databricks-agent",
    evaluators=evaluators,
    evaluator_config=evaluator_config,
    experiment_name="/Shared/health_monitor_agent_evaluation",
    run_name=run_name,  # ✅ Consistent naming
)

# Query latest evaluation
runs = mlflow.search_runs(
    filter_string="tags.mlflow.runName LIKE 'eval_pre_deploy_%'",  # ✅ Predictable
    order_by=["start_time DESC"],
    max_results=1
)
```

**Why this matters:**
- Automated checks can find latest evaluation results
- Consistent naming enables programmatic threshold validation
- CI/CD pipelines can query recent evaluation metrics

---

## Quick Example: @scorer Decorator Pattern

```python
import mlflow
from mlflow.models import Score
from mlflow.metrics import scorer
from typing import Dict, Optional

# Import helpers (from scripts/evaluation_helpers.py)
from evaluation_helpers import _extract_response_text, _call_llm_for_scoring

@mlflow.trace(name="cost_accuracy_judge", span_type="JUDGE")
@scorer
def cost_accuracy_judge(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """
    Custom judge evaluating cost accuracy in agent responses.
    
    CRITICAL: Must use _extract_response_text() helper.
    """
    # ✅ STEP 1: Extract response text (MANDATORY)
    response_text = _extract_response_text(outputs)
    
    # ✅ STEP 2: Get query
    query = inputs.get("request", "")
    
    # ✅ STEP 3: Build evaluation prompt
    judge_prompt = f"""Evaluate cost accuracy...
    
    Query: {query}
    Response: {response_text}
    
    Return JSON: {{"score": 0.0-1.0, "rationale": "explanation"}}
    """
    
    # ✅ STEP 4: Call LLM via Databricks SDK (NOT langchain_databricks)
    result = _call_llm_for_scoring(judge_prompt, endpoint="databricks-claude-3-7-sonnet")
    
    # ✅ STEP 5: Return Score object
    return Score(
        value=result["score"],
        rationale=result["rationale"]
    )
```

**See `references/custom-scorer-patterns.md` for complete examples.**

---

## CRITICAL: `make_judge()` Template Variable Constraints

`make_judge()` and the MLflow Prompt Registry use the same `{{ }}` template syntax but have **different validation rules**:

| System | Allowed Variable Names | Validation |
|--------|----------------------|------------|
| Prompt Registry (`register_prompt()`) | Any `{{ variable }}` | No validation — any name accepted |
| `make_judge(instructions=...)` | Only 5 allowed (see below) | Strict — raises `MlflowException` on unknown variables |

**`make_judge()` only permits these 5 template variables:**
- `{{ inputs }}` — the eval record's `inputs` dict
- `{{ outputs }}` — the `predict_fn` return value
- `{{ trace }}` — the MLflow trace from `predict_fn`
- `{{ expectations }}` — the eval record's `expectations` dict
- `{{ conversation }}` — conversation data (for chat models)

**Bidirectional constraint:**
1. MUST contain **at least one** of the 5 allowed variables (plain text is rejected)
2. MUST NOT contain **any other** `{{ variable }}` names (custom variables are rejected)

```python
# WRONG — custom variables crash make_judge()
"Question: {{question}}\nExpected SQL: {{expected_sql}}\nGenerated SQL: {{genie_sql}}"

# WRONG — no variables at all, also crashes make_judge()
"Evaluate the SQL quality and respond with yes or no."

# CORRECT — uses only allowed variables
"User question: {{ inputs }}\nGenerated SQL: {{ outputs }}\nExpected SQL: {{ expectations }}"
```

---

## CRITICAL: `predict_fn` Keyword Argument Contract

`mlflow.genai.evaluate()` **unpacks** the `inputs` dict as keyword arguments when calling `predict_fn`. The function signature must match the keys in `eval_records["inputs"]`.

```python
# Given eval records with:
eval_records = [{"inputs": {"question": "...", "space_id": "...", "expected_sql": "..."}, ...}]

# WRONG — receives keyword args, not a dict
def predict_fn(inputs: dict) -> dict:
    question = inputs["question"]  # TypeError or MlflowException

# CORRECT — signature matches input keys
def predict_fn(question: str, expected_sql: str = "", **kwargs) -> dict:
    # question and expected_sql are unpacked directly
    # space_id, catalog, etc. land in **kwargs (use closure for these)
    ...
```

---

## Metric Aliases Quick Reference

**CRITICAL: Handle metric name variations across MLflow versions.**

```python
# Built-in scorers use different metric names across MLflow versions
METRIC_ALIASES = {
    "relevance/mean": ["relevance_to_query/mean"],  # MLflow 3.0 vs 3.1
    "safety/mean": ["safety/mean"],  # No alias needed
    "guidelines/mean": ["guidelines/mean"],  # No alias needed
}
```

**Why aliases matter:**
- MLflow 3.0 uses `"relevance/mean"`
- MLflow 3.1 uses `"relevance_to_query/mean"`
- Without aliases, threshold checks fail silently
- Deployment succeeds with failing scores (BAD!)

**See `references/threshold-checking.md` for complete `check_thresholds()` function.**

---

## Foundation Model Endpoints Recommendation

**ALWAYS use foundation model endpoints (NOT pay-per-token) for judges.**

### ✅ Recommended Endpoints

- `endpoints:/databricks-claude-sonnet-4-5` (recommended)
- `endpoints:/databricks-meta-llama-3-1-405b-instruct`
- `endpoints:/databricks-claude-3-7-sonnet`

### ❌ Avoid Pay-Per-Token Endpoints

- Evaluation is high-volume
- Pay-per-token gets expensive fast
- Foundation models included in workspace DBU consumption

**See `references/custom-scorer-patterns.md` for complete endpoint list.**

---

## Validation Checklist

Before running agent evaluation:

### Dataset & Configuration
- [ ] Evaluation dataset loaded with correct schema (request, response columns)
- [ ] 4-6 essential guidelines defined (not 8+)
- [ ] Run name follows convention: `eval_pre_deploy_YYYYMMDD_HHMMSS`
- [ ] Evaluation experiment set correctly

### Custom Scorers (CRITICAL)
- [ ] ✅ **`_extract_response_text()` helper included in ALL custom scorers**
- [ ] ✅ **Databricks SDK used for LLM calls (NOT `langchain_databricks`)**
- [ ] ✅ **`_call_llm_for_scoring()` helper defined and used**
- [ ] Custom judges use `@mlflow.trace` and `@scorer` decorators
- [ ] Custom judges return `Score` object with `value` and `rationale`
- [ ] Foundation model endpoints used (not pay-per-token)
- [ ] Temperature = 0.0 for judge consistency

### Threshold Checking
- [ ] ✅ **`METRIC_ALIASES` defined for backward compatibility**
- [ ] ✅ **`check_thresholds()` function used (handles aliases)**
- [ ] Thresholds defined for all judges
- [ ] Results checked against thresholds before deployment

---

## Reference Files

- **`references/custom-scorer-patterns.md`** - Complete custom scorer patterns with `_call_llm_for_scoring()` helper
- **`references/built-in-judges.md`** - Built-in judges (relevance, safety, guidelines) with thresholds
- **`references/threshold-checking.md`** - `check_thresholds()` function with metric aliases support
- **`references/evaluation-dataset-patterns.md`** - Evaluation dataset schema and loading patterns
- **`scripts/evaluation_helpers.py`** - Complete helper functions (`_extract_response_text()`, `_call_llm_for_scoring()`, `check_thresholds()`)

---

## References

### Official Documentation
- [MLflow GenAI Evaluate](https://mlflow.org/docs/latest/llms/llm-evaluate/)
- [MLflow Custom Metrics](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html#creating-custom-llm-evaluation-metrics)
- [Databricks Agent Evaluation](https://docs.databricks.com/en/generative-ai/agent-evaluation/)
- [LLM-as-Judge Pattern](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html#llm-as-judge-metrics)

### Related Skills
- `ml-pipeline-setup` - MLflow model patterns
- `responses-agent-patterns` - ResponsesAgent implementation patterns

---

## Scorer vs Evaluator Semantics

`make_judge()` returns an **`InstructionsJudge` scorer callable** — an object intended for use inside `mlflow.genai.evaluate(scorers=[...])`. Scorers are **not standalone evaluators**:

- **Scorers** are callables that receive structured inputs from `mlflow.genai.evaluate()` and return `Feedback` objects. They have no `.evaluate()` method.
- **`mlflow.genai.evaluate()`** is the evaluator — it orchestrates the predict function, passes data through scorers, and logs results to MLflow.

For inline/conditional LLM calls **outside** the `mlflow.genai.evaluate()` harness (e.g., arbiter conditional scoring, ad-hoc quality checks), use direct LLM calls:
- `_call_llm_for_scoring()` via `w.serving_endpoints.query()` (Databricks SDK)
- Parse JSON verdicts from the LLM response manually

| Use Case | Correct Approach | Wrong Approach |
|----------|-----------------|----------------|
| Running all judges on benchmark suite | `mlflow.genai.evaluate(scorers=[judge1, judge2])` | Calling each judge manually in a loop |
| Conditional scoring (arbiter fires only on disagreement) | `_call_llm_for_scoring(prompt)` inside a `@scorer` | `make_judge().evaluate(data)` — no `.evaluate()` method |
| Quick ad-hoc LLM quality check | `w.serving_endpoints.query(...)` | `make_judge()(inputs)` — wrong call signature |

### Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Calling `make_judge().evaluate()` for standalone scoring | `AttributeError: 'InstructionsJudge' object has no attribute 'evaluate'` | Use `_call_llm_for_scoring()` for inline/conditional LLM calls, or pass scorers to `mlflow.genai.evaluate(scorers=[...])` |

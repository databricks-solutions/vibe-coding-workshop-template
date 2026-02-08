---
name: mlflow-genai-evaluation
description: >
  MLflow GenAI evaluation patterns with LLM judges, custom scorers with _extract_response_text()
  helper, Databricks SDK for scorer LLM calls, metric aliases, threshold checking, 4-6
  guidelines best practice, foundation model endpoints. Use when implementing agent evaluation
  pipelines, creating custom LLM judges, setting up evaluation datasets, checking deployment
  thresholds, or troubleshooting evaluation errors.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
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

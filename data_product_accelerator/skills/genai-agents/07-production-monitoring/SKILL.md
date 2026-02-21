---
name: production-monitoring
description: >
  Continuous production monitoring for GenAI agents - registered scorers with sampling,
  on-demand assess(), scorer lifecycle, trace archival, metric backfill. Use when setting
  up production monitoring, creating registered scorers, implementing sampling strategies,
  archiving traces, or backfilling historical metrics. Triggers on "monitoring", "production",
  "scorer", "sampling", "assess", "trace archival", "backfill".
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
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-agent-bricks/SKILL.md"
      relationship: "reference"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Production Monitoring Patterns

Production-grade patterns for continuous monitoring of GenAI agents in production using MLflow registered scorers, on-demand assessment, trace archival, and metric backfill.

## When to Use

- Setting up continuous production monitoring for GenAI agents
- Creating registered scorers with sampling strategies
- Implementing on-demand evaluation workflows
- Archiving MLflow traces for analysis
- Backfilling historical metrics
- Troubleshooting production scorer failures

---

## Two Approaches: Registered Scorers vs On-Demand assess()

| Approach | Use Case | Sampling | Cost |
|---|---|---|---|
| **Registered Scorers** | Continuous monitoring | Configurable (1-100%) | Higher (continuous) |
| **On-Demand assess()** | Periodic evaluation | 100% (when run) | Lower (on-demand) |

### Registered Scorers (Continuous)

```python
from mlflow.models import scorer
from mlflow.metrics import Score

@scorer
def safety_scorer(inputs, outputs, expectations=None):
    # Scorer logic
    return Score(value=0.95, rationale="...")

# Register scorer
mlflow.models.register_scorer(
    scorer=safety_scorer,
    name="safety_scorer",
    sampling_rate=0.1  # 10% sampling
)

# Start scorer (begins continuous monitoring)
scorer_instance = mlflow.models.start_scorer("safety_scorer")
```

**For complete registered scorer patterns, see:** `references/registered-scorers.md`

### On-Demand assess()

```python
# Evaluate specific traces on-demand
results = mlflow.genai.assess(
    traces=traces_df,
    evaluators=[safety_scorer, relevance_scorer]
)
```

**Use when:**
- Periodic evaluation (weekly, monthly)
- Ad-hoc analysis
- Cost optimization (evaluate only when needed)

---

## ⚠️ CRITICAL: Immutable Scorer Pattern

**MANDATORY: Scorers must be immutable - `scorer = scorer.start()` pattern.**

### ❌ WRONG: Mutable Scorer

```python
scorer = mlflow.models.register_scorer(...)
scorer.start()  # ❌ Modifies scorer object
scorer.stop()   # ❌ May not work correctly
```

### ✅ CORRECT: Immutable Pattern

```python
scorer = mlflow.models.register_scorer(...)
scorer_instance = scorer.start()  # ✅ Returns new instance
scorer_instance.stop()  # ✅ Works correctly
```

**Why this matters:**
- Scorer lifecycle operations require immutable pattern
- Prevents state corruption
- Enables proper start/stop/delete operations

**For complete immutable patterns, see:** `references/registered-scorers.md`

---

## Registered Scorer Quick Pattern with Sampling

```python
from mlflow.models import scorer
from mlflow.metrics import Score

@scorer
def safety_scorer(inputs, outputs, expectations=None):
    """Safety scorer with 10% sampling."""
    response_text = _extract_response_text(outputs)
    # ... scoring logic
    return Score(value=0.95, rationale="Safe response")

# Register with sampling
safety_scorer_registered = mlflow.models.register_scorer(
    scorer=safety_scorer,
    name="safety_scorer",
    sampling_rate=0.1  # 10% of traces evaluated
)

# Start continuous monitoring
safety_scorer_instance = safety_scorer_registered.start()
```

**Sampling rates by scorer type:**
- **Safety**: 100% (critical)
- **Relevance**: 10-20% (moderate volume)
- **Guidelines**: 5-10% (lower priority)
- **Custom**: 1-5% (cost optimization)

---

## Custom Heuristic Scorer Pattern (Fast, 100% Sampling)

```python
@scorer
def fast_heuristic_scorer(inputs, outputs, expectations=None):
    """
    Fast heuristic scorer - runs on 100% of traces.
    
    Use for lightweight checks (length, format, keywords).
    """
    response_text = _extract_response_text(outputs)
    
    # Fast checks
    score = 1.0
    issues = []
    
    if len(response_text) < 10:
        score -= 0.5
        issues.append("Response too short")
    
    if "ERROR" in response_text.upper():
        score -= 0.3
        issues.append("Contains error keyword")
    
    return Score(
        value=max(0.0, score),
        rationale="; ".join(issues) if issues else "Passed heuristic checks"
    )
```

---

## On-Demand assess() Pattern

```python
def evaluate_production_traces(
    start_time: datetime,
    end_time: datetime,
    evaluators: list
):
    """
    Evaluate production traces on-demand.
    
    Useful for periodic evaluation or ad-hoc analysis.
    """
    # Query traces from time range
    traces_df = query_traces(start_time, end_time)
    
    # Run evaluation
    results = mlflow.genai.assess(
        traces=traces_df,
        evaluators=evaluators,
        experiment_name="/Shared/health_monitor_agent/production_eval"
    )
    
    return results
```

---

## Trace Archival Quick Setup

```python
import mlflow

# Enable trace archival to Unity Catalog
mlflow.enable_databricks_trace_archival(
    catalog="catalog",
    schema="schema",
    table="agent_traces"
)

# Traces automatically archived to Delta table
# Query: SELECT * FROM catalog.schema.agent_traces
```

**For complete trace archival patterns, see:** `references/trace-archival.md`

---

## Production vs Dev Evaluation Comparison

| Aspect | Development | Production |
|---|---|---|
| **Method** | `mlflow.genai.evaluate()` | Registered scorers + `assess()` |
| **Sampling** | 100% (full dataset) | Configurable (1-100%) |
| **Frequency** | On-demand | Continuous + periodic |
| **Cost** | Low (one-time) | Higher (continuous) |
| **Dataset** | Static eval dataset | Live production traces |
| **Thresholds** | Pre-deployment gates | Continuous monitoring |

---

## Unified Scorer Definitions Concept

Define scorers once, use in both development and production:

```python
# Define scorer (reusable)
@scorer
def safety_scorer(inputs, outputs, expectations=None):
    # ... scorer logic
    return Score(value=0.95, rationale="...")

# Use in development evaluation
results = mlflow.genai.evaluate(
    model=model_uri,
    data=eval_dataset,
    evaluators=[safety_scorer]
)

# Use in production (register + start)
safety_registered = mlflow.models.register_scorer(
    scorer=safety_scorer,
    name="safety_scorer",
    sampling_rate=1.0
)
safety_registered.start()
```

---

## ❌/✅ Patterns

### Immutable Pattern

```python
# ✅ CORRECT: Immutable pattern
scorer = mlflow.models.register_scorer(...)
scorer_instance = scorer.start()  # Returns new instance
scorer_instance.stop()

# ❌ WRONG: Mutable pattern
scorer = mlflow.models.register_scorer(...)
scorer.start()  # Modifies scorer object
scorer.stop()   # May not work
```

### External Imports in Scorers

```python
# ✅ CORRECT: Import helpers inside scorer
@scorer
def safety_scorer(inputs, outputs, expectations=None):
    from evaluation_helpers import _extract_response_text
    response_text = _extract_response_text(outputs)
    # ...

# ❌ WRONG: External imports at module level
from evaluation_helpers import _extract_response_text  # ❌ May fail in production

@scorer
def safety_scorer(inputs, outputs, expectations=None):
    response_text = _extract_response_text(outputs)
    # ...
```

---

## Validation Checklist

Before deploying production monitoring:

### Registered Scorers
- [ ] ✅ **Immutable pattern used (`scorer = scorer.start()`)**
- [ ] ✅ **Sampling rates configured appropriately**
- [ ] ✅ **Scorer lifecycle managed (register/start/stop/delete)**
- [ ] ✅ **External imports inside scorer functions**

### On-Demand Assessment
- [ ] `assess()` function implemented for periodic evaluation
- [ ] Trace querying patterns implemented
- [ ] Results logged to experiments

### Trace Archival
- [ ] Trace archival enabled
- [ ] Delta table schema configured
- [ ] Query patterns for archived traces

### Metric Backfill
- [ ] Backfill workflow implemented (if needed)
- [ ] Historical analysis patterns defined

---

## Reference Files

- **`references/registered-scorers.md`** - Complete registered scorer patterns with lifecycle management
- **`references/trace-archival.md`** - Trace archival setup and querying patterns
- **`references/metric-backfill.md`** - Backfill patterns for historical metrics
- **`references/monitoring-dashboard-queries.md`** - SQL queries for monitoring dashboards
- **`scripts/register_production_scorers.py`** - Complete script to register all production scorers

---

## References

### Official Documentation
- [MLflow Registered Scorers](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html#registered-scorers)
- [MLflow Trace Archival](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage)
- [MLflow assess()](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html#assess)

### Related Skills
- `mlflow-genai-evaluation` - Development evaluation patterns
- `deployment-automation` - Deployment workflows
- `responses-agent-patterns` - ResponsesAgent implementation

---

## Version History

| Date | Changes |
|---|---|
| Feb 6, 2026 | Initial version: Production monitoring with immutable scorer pattern |

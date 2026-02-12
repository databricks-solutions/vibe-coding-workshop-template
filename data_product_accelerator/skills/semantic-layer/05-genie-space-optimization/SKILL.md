---
name: genie-space-optimization
description: Interactive Genie Space optimization loop that writes benchmark questions, queries Genie via Conversation API, evaluates accuracy and repeatability, applies changes through six control levers (UC metadata, Metric Views, TVFs, Monitoring tables, ML tables, Genie Instructions), and re-tests until targets are met. Use when optimizing Genie Space accuracy (target 95%+) or repeatability (target 90%+), debugging incorrect SQL generation, improving asset routing, or running automated optimization sessions. Triggers on "optimize Genie", "Genie accuracy", "Genie repeatability", "benchmark questions", "test Genie", "Genie control levers", "Genie optimization loop".
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: semantic-layer
  role: worker
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  called_by:
    - semantic-layer-setup
  standalone: true
  source: 34-genie-space-optimization.mdc
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-genie/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# Genie Space Optimization

Interactive, agent-driven optimization loop that improves Genie Space quality through systematic benchmark testing, evaluation, and iterative control lever adjustments.

## When to Use This Skill

- Optimizing Genie Space accuracy or repeatability scores
- Writing benchmark questions for a new or existing Genie Space
- Debugging incorrect SQL generation from Genie
- Improving asset routing (TVF vs Metric View selection)
- Running automated optimization sessions against live Genie Spaces
- Updating Genie Space configurations via API after testing
- Managing Genie export JSON files with dual persistence

### Hand Off to Related Skills

| User Says / Task Involves | Load Instead |
|---|---|
| "create Genie Space from scratch" | `genie-space-patterns` |
| "deploy Genie Space via API" | `genie-space-export-import-api` |
| "create metric view" | `metric-views-patterns` |
| "create TVF" | `databricks-table-valued-functions` |

**This skill** covers the *optimization loop*: test → evaluate → adjust → re-test.
Other skills cover *creation* and *deployment* of individual assets.

---

## Quality Dimensions

| Dimension | Target | Definition |
|-----------|--------|------------|
| **Accuracy** | 95%+ | Does Genie return correct SQL/answers for benchmark questions? |
| **Repeatability** | 90%+ | Does the same question produce the same SQL across multiple runs? |

---

## Core Optimization Loop

```
┌──────────────────────────────────────────────────────┐
│  1. WRITE BENCHMARKS                                  │
│     Generate domain-relevant benchmark questions      │
│     with expected SQL answers                         │
├──────────────────────────────────────────────────────┤
│  2. QUERY GENIE                                       │
│     Run benchmarks via Conversation API               │
│     (respect 12s rate limit between queries)          │
├──────────────────────────────────────────────────────┤
│  3. EVALUATE                                          │
│     Compare generated SQL to expected SQL             │
│     Measure accuracy + repeatability                  │
├──────────────────────────────────────────────────────┤
│  4. DIAGNOSE                                          │
│     Identify failure patterns:                        │
│     - Wrong asset selected (TVF vs MV vs Table)       │
│     - Wrong columns/aggregations                      │
│     - Missing routing context                         │
├──────────────────────────────────────────────────────┤
│  5. APPLY CONTROL LEVERS                              │
│     Fix issues using 6 levers (priority order)        │
│     Apply via BOTH API + repository (dual persist)    │
├──────────────────────────────────────────────────────┤
│  6. RE-TEST                                           │
│     Wait 30s → re-run failing questions               │
│     Measure improvement                               │
│     Loop back to step 4 if targets not met            │
├──────────────────────────────────────────────────────┤
│  7. DOCUMENT                                          │
│     Generate optimization report with metrics         │
└──────────────────────────────────────────────────────┘
```

---

## Step 1: Write Benchmark Questions

Generate benchmark questions that cover the domain's key use cases. Each question must have:

1. **Natural language question** (what a user would ask)
2. **Expected SQL** (tested, working SQL)
3. **Expected asset** (MV, TVF, or TABLE)
4. **Category** (aggregation, list, time-series, comparison, etc.)

### Asset Routing Rules for Benchmarks

| Question Type | Expected Asset | Example |
|--------------|----------------|---------|
| Total/average/overall | Metric View | "What is total spend?" |
| Top N / list / show me | TVF | "Show top 10 costliest jobs" |
| Date-range analysis | TVF | "Daily costs for last month" |
| KPI / single value | Metric View | "Average job duration" |
| Drill-down / detail | TVF | "Details for workspace X" |

See [Benchmark Patterns](references/benchmark-patterns.md) for complete question-writing guide.

### Quick Benchmark Template

```yaml
benchmarks:
  - id: "cost_001"
    question: "What is total spend this month?"
    expected_sql: "SELECT MEASURE(total_cost) FROM ${catalog}.${schema}.mv_cost_analytics WHERE ..."
    expected_asset: "MV"
    category: "aggregation"

  - id: "cost_002"
    question: "Show top 10 costliest workspaces"
    expected_sql: "SELECT * FROM ${catalog}.${schema}.get_top_cost_contributors('7', 'workspace')"
    expected_asset: "TVF"
    category: "list"
```

See [Golden Queries Template](assets/templates/golden-queries.yaml) for the full YAML format.

---

## Step 2: Query Genie via API

### Core Query Function

```python
import time
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

def run_genie_query(space_id: str, question: str, max_wait: int = 120) -> dict:
    """Execute a query against Genie and return SQL + status."""
    try:
        resp = w.genie.start_conversation(space_id=space_id, content=question)
        conversation_id = resp.conversation_id
        message_id = resp.message_id

        poll_interval = 3
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(poll_interval)
            msg = w.genie.get_message(
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id
            )
            status = str(msg.status) if hasattr(msg, 'status') else 'UNKNOWN'
            if any(s in status for s in ['COMPLETED', 'FAILED', 'CANCELLED']):
                break
            poll_interval = min(poll_interval + 1, 10)

        sql = None
        if hasattr(msg, 'attachments') and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, 'query') and att.query:
                    sql = att.query.query if hasattr(att.query, 'query') else str(att.query)
        return {"status": status, "sql": sql}
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}
```

### Rate Limiting (CRITICAL)

Databricks enforces **5 POST requests/minute/workspace**. Always wait **12+ seconds** between queries:

```python
time.sleep(12)  # MANDATORY between every Genie API call
```

---

## Step 3: Evaluate Results

### Accuracy Evaluation

Compare generated SQL against expected SQL:

```python
def evaluate_accuracy(result: dict, expected: dict) -> dict:
    """Evaluate if Genie returned correct SQL."""
    generated_sql = (result.get("sql") or "").lower().strip()
    expected_sql = expected.get("expected_sql", "").lower().strip()

    # Check asset routing
    expected_asset = expected.get("expected_asset", "").upper()
    uses_mv = "mv_" in generated_sql or "measure(" in generated_sql
    uses_tvf = "get_" in generated_sql
    actual_asset = "MV" if uses_mv else ("TVF" if uses_tvf else "TABLE")

    return {
        "question": expected["question"],
        "sql_generated": result.get("status") == "COMPLETED" and bool(generated_sql),
        "correct_asset": actual_asset == expected_asset,
        "actual_asset": actual_asset,
        "expected_asset": expected_asset,
    }
```

### Repeatability Testing

Run each question 3 times and measure consistency:

```python
import hashlib
from collections import Counter

def test_repeatability(space_id: str, question: str, iterations: int = 3) -> dict:
    """Test SQL consistency across multiple runs."""
    hashes = []
    for i in range(iterations):
        sql = run_genie_query(space_id, question).get("sql", "")
        sql_hash = hashlib.md5(sql.lower().encode()).hexdigest()[:8] if sql else "NONE"
        hashes.append(sql_hash)
        time.sleep(12)

    most_common_count = Counter(hashes).most_common(1)[0][1]
    return {
        "question": question,
        "repeatability_pct": (most_common_count / len(hashes)) * 100,
        "unique_variants": len(set(hashes)),
    }
```

### Score Thresholds

| Score | Classification | Action Required |
|-------|---------------|-----------------|
| **100%** | Identical | No action needed |
| **70-99%** | Minor variance | Usually acceptable |
| **50-69%** | Significant variance | Update instructions or add sample query |
| **<50%** | Critical variance | Must fix with explicit routing rules |

---

## Step 4: Diagnose Failures

Common failure patterns and their root causes:

| Symptom | Root Cause | Lever to Fix |
|---------|-----------|--------------|
| Wrong asset selected (MV vs TVF) | Ambiguous routing | Genie Instructions (lever 6) |
| Wrong columns in query | Poor column descriptions | UC Table/Column comments (lever 1) |
| Missing aggregation | Metric view not discoverable | Metric View metadata (lever 2) |
| Wrong parameters to TVF | TVF comment unclear | TVF COMMENT (lever 3) |
| Inconsistent SQL across runs | Ambiguous question mapping | Genie Instructions + sample query |
| Query returns no data | Wrong date range defaults | Genie Instructions (time defaults) |

---

## Step 5: Apply Control Levers (Priority Order)

Six levers to fix Genie behavior, applied **in priority order**:

| Priority | Lever | Durability | Char Limit | When to Use |
|----------|-------|------------|------------|-------------|
| **1** | UC Tables & Columns | Highest | Unlimited | Column misunderstanding, wrong tables |
| **2** | Metric Views | High | N/A | Metric/aggregation questions wrong |
| **3** | TVFs (Functions) | High | N/A | Complex calculation errors |
| **4** | Monitoring Tables | Medium | Unlimited | Time-series queries wrong |
| **5** | ML Model Tables | Medium | Unlimited | Prediction queries wrong |
| **6** | Genie Instructions | Lowest | ~4000 chars | Asset routing, last resort |

**Why this order?** UC metadata survives Genie Space rebuilds. Genie Instructions have a ~4000 char limit and are the least durable.

### Dual Persistence (CRITICAL)

**Every optimization MUST be applied in TWO places:**

| Step | Action | Why |
|------|--------|-----|
| **1. Direct Update** | API call or ALTER TABLE | Effective immediately |
| **2. Repository Update** | Update source files | Persists across deployments |

See [Control Levers Reference](references/control-levers.md) for detailed per-lever update patterns.

---

## Step 6: Re-Test and Iterate

After applying changes:

1. **Wait 30 seconds** for propagation
2. **Re-run only failing/variable questions** (not full suite)
3. **Measure improvement** (compare before/after)
4. **Loop back to Step 4** if targets not met

```python
# Re-test after optimization
time.sleep(30)  # Wait for propagation

for question in failing_questions:
    result = run_genie_query(space_id, question["question"])
    evaluation = evaluate_accuracy(result, question)
    print(f"  {'PASS' if evaluation['correct_asset'] else 'FAIL'}: {question['question']}")
    time.sleep(12)
```

---

## Step 7: Document Results

Generate an optimization report using the [Report Template](assets/templates/optimization-report.md).

Key sections:
- Executive summary with before/after metrics
- Per-question test results
- Optimizations applied (which levers, what changed)
- Dual persistence confirmation
- Files updated

---

## Scripts

### [genie_optimizer.py](scripts/genie_optimizer.py)
Complete optimization loop: load benchmarks → query Genie → evaluate → report.

```bash
# Run from Databricks notebook or local with SDK configured
python scripts/genie_optimizer.py --space-id <ID> --benchmarks golden-queries.yaml
```

### [repeatability_tester.py](scripts/repeatability_tester.py)
Standalone repeatability testing with configurable iterations.

```bash
python scripts/repeatability_tester.py --space-id <ID> --iterations 3
```

---

## Reference Files

- **[Control Levers](references/control-levers.md)**: Detailed per-lever update patterns, SQL commands, API calls, and repository file mappings for dual persistence
- **[Optimization Workflow](references/optimization-workflow.md)**: Extended step-by-step workflow with decision trees, failure pattern analysis, and advanced techniques
- **[Benchmark Patterns](references/benchmark-patterns.md)**: Complete guide to writing effective benchmark questions including category coverage, SQL templates, and domain-specific patterns

---

## Validation Checklist

### Before Optimization
- [ ] Correct Space ID identified (see domain reference table)
- [ ] Benchmark questions loaded with expected SQL
- [ ] Current Genie export config backed up
- [ ] Rate limiting in place (12s between queries)

### During Optimization
- [ ] Accuracy tests run for all benchmark questions
- [ ] Repeatability tests run (2-3 iterations per question)
- [ ] Root causes identified for each failure
- [ ] Control levers applied in priority order (1-6)

### After Optimization
- [ ] Direct update applied (API/ALTER TABLE)
- [ ] Repository file updated (dual persistence)
- [ ] Template variables preserved (`${catalog}`, `${gold_schema}`)
- [ ] All arrays sorted in Genie export JSON
- [ ] Wait 30s, then re-test failing questions
- [ ] Improvement measured and documented
- [ ] Optimization report generated

---

## Common Mistakes

### Forgetting Array Sorting in API Updates
```python
# WRONG: Unsorted → "data_sources.tables must be sorted"
payload = {"serialized_space": json.dumps(config)}

# CORRECT: Sort all arrays first
config = sort_genie_config(config)
payload = {"serialized_space": json.dumps(config)}
```

### Skipping Dual Persistence
```python
# WRONG: API-only update (lost on next deployment)
subprocess.run(["databricks", "api", "patch", ...])

# CORRECT: API + repository
subprocess.run(["databricks", "api", "patch", ...])         # Direct
with open("src/genie/config.json", "w") as f: json.dump(...)  # Repository
```

### Ignoring Rate Limits
```python
# WRONG: Rapid-fire → queries fail silently
for q in questions: run_genie_query(space_id, q)

# CORRECT: 12s between each query
for q in questions:
    run_genie_query(space_id, q)
    time.sleep(12)
```

### Putting Everything in Genie Instructions
Instructions have a ~4000 char limit. Fix column descriptions first (lever 1), then metric views (lever 2), then TVFs (lever 3). Use instructions only for routing rules.

---

## Related Skills

- **`genie-space-patterns`** - Initial Genie Space creation and setup
- **`genie-space-export-import-api`** - Programmatic deployment via REST API
- **`metric-views-patterns`** - Metric view creation and validation
- **`databricks-table-valued-functions`** - TVF creation for Genie

---

## References

### Official Databricks Documentation
- [Genie API Reference](https://docs.databricks.com/api/workspace/genie)
- [Genie Space Configuration](https://docs.databricks.com/genie/spaces)
- [Genie Conversation API](https://docs.databricks.com/api/workspace/genie/startconversation)

---

## Version History

- **v1.0** (Feb 2026) - Initial skill converted from `34-genie-space-optimization.mdc`
  - Interactive optimization loop (write → query → evaluate → adjust → re-test)
  - Six control levers with priority ordering
  - Dual persistence requirement for all changes
  - Repeatability testing methodology
  - Benchmark question writing patterns
  - Domain-specific Space ID reference
  - Rate limiting enforcement (12s between queries)
  - Benchmarked results: Quality 100%, Reliability 80%, Security 67%, Performance 47%
  - Key discovery: TVF-first routing improves repeatability

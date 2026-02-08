# Optimization Workflow Reference

Extended step-by-step workflow with decision trees, failure analysis, and advanced techniques.

---

## Pre-Optimization Setup

### 1. Identify Target Space

Use the domain-to-Space-ID mapping for your project:

```python
# Example domain-space mapping (customize for your project)
DOMAIN_SPACES = {
    "cost":        "01f0f1a3c2dc1c8897de11d27ca2cb6f",
    "reliability": "01f0f1a3c33b19848c856518eac91dee",
    "quality":     "01f0f1a3c39517ffbe190f38956d8dd1",
    "performance": "01f0f1a3c3e31a8e8e6dee3eddf5d61f",
    "security":    "01f0f1a3c44117acada010638189392f",
    "unified":     "01f0f1a3c4981080b61e224ecd465817",
}
```

### 2. Load Benchmark Questions

```python
import yaml

with open("tests/optimizer/genie_golden_queries.yml") as f:
    benchmarks = yaml.safe_load(f)

domain_questions = benchmarks.get("cost", [])
print(f"Loaded {len(domain_questions)} benchmark questions for cost domain")
```

### 3. Back Up Current Config

```python
import json
import shutil
from datetime import datetime

domain = "cost_intelligence"
source = f"src/genie/{domain}_genie_export.json"
backup = f"src/genie/backups/{domain}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
shutil.copy2(source, backup)
print(f"Backed up to {backup}")
```

---

## Phase 1: Initial Assessment

### Run Accuracy Tests

```python
results = []
for q in domain_questions:
    print(f"Testing: {q['question'][:60]}...", end=" ")
    result = run_genie_query(SPACE_ID, q["question"])
    evaluation = evaluate_accuracy(result, q)
    results.append(evaluation)
    status = "PASS" if evaluation["correct_asset"] else "FAIL"
    print(f"{status} (expected={q['expected_asset']}, got={evaluation['actual_asset']})")
    time.sleep(12)

# Calculate accuracy
accuracy = sum(1 for r in results if r["correct_asset"]) / len(results) * 100
print(f"\nAccuracy: {accuracy:.0f}% ({sum(1 for r in results if r['correct_asset'])}/{len(results)})")
```

### Run Repeatability Tests

Focus on questions that passed accuracy but may be inconsistent:

```python
repeat_results = []
for q in domain_questions[:5]:  # Test top 5 questions
    print(f"\nRepeatability: {q['question'][:50]}...")
    repeat = test_repeatability(SPACE_ID, q["question"], iterations=3)
    repeat_results.append(repeat)
    print(f"  Score: {repeat['repeatability_pct']:.0f}% ({repeat['unique_variants']} variants)")

avg_repeatability = sum(r["repeatability_pct"] for r in repeat_results) / len(repeat_results)
print(f"\nAverage Repeatability: {avg_repeatability:.0f}%")
```

---

## Phase 2: Failure Analysis

### Decision Tree for Root Cause

```
Question failed?
├── SQL not generated (status != COMPLETED)
│   ├── Check: Is the table/view accessible?
│   ├── Check: Does the question match any trusted asset?
│   └── Fix: Add table/view comments (lever 1) or instructions (lever 6)
│
├── Wrong asset selected
│   ├── Expected MV, got TABLE → Metric view not discoverable
│   │   └── Fix: Update MV description (lever 2) + routing rule (lever 6)
│   ├── Expected TVF, got MV → TVF comment missing "when to use"
│   │   └── Fix: Update TVF COMMENT (lever 3) + routing rule (lever 6)
│   └── Expected MV, got TVF → Conflicting routing rules
│       └── Fix: Clarify instructions (lever 6), group by question type
│
├── Correct asset but wrong SQL
│   ├── Wrong columns → Column COMMENT unclear
│   │   └── Fix: Update column COMMENT (lever 1)
│   ├── Wrong aggregation → Measure description unclear
│   │   └── Fix: Update MV measure description (lever 2)
│   ├── Wrong parameters → TVF COMMENT missing examples
│   │   └── Fix: Update TVF COMMENT with examples (lever 3)
│   └── Wrong date range → No default specified
│       └── Fix: Add time defaults to instructions (lever 6)
│
└── Low repeatability (correct but inconsistent)
    ├── Multiple valid paths → Add sample query for canonical path
    │   └── Fix: Add example_question_sql (lever 6)
    ├── Ambiguous terms → Define explicitly
    │   └── Fix: Add term definitions to instructions (lever 6)
    └── Asset ambiguity → Make routing deterministic
        └── Fix: "For X queries, ALWAYS use Y asset" (lever 6)
```

### Categorize Failures

```python
failure_categories = {
    "wrong_asset": [],
    "no_sql": [],
    "wrong_columns": [],
    "low_repeatability": [],
}

for r in results:
    if not r["sql_generated"]:
        failure_categories["no_sql"].append(r)
    elif not r["correct_asset"]:
        failure_categories["wrong_asset"].append(r)

for r in repeat_results:
    if r["repeatability_pct"] < 70:
        failure_categories["low_repeatability"].append(r)

for category, items in failure_categories.items():
    print(f"\n{category}: {len(items)} issues")
    for item in items:
        print(f"  - {item['question'][:60]}")
```

---

## Phase 3: Apply Fixes

### Fix Pattern: Wrong Asset Routing

When Genie selects the wrong asset type:

1. **First:** Update the preferred asset's metadata (levers 1-3)
   - Add "Use this for [question type]" to description/COMMENT
   - Make the asset more discoverable

2. **Then:** Add explicit routing rules to instructions (lever 6)
   ```
   === ROUTING RULES ===
   "total cost" / "overall spend" → USE mv_cost_analytics
   "top N" / "costliest" / "breakdown" → USE get_top_cost_contributors
   ```

3. **If still failing:** Add example_question_sql to Genie config
   ```json
   {
     "instructions": {
       "example_question_sqls": [
         {
           "id": "abc123...",
           "question": ["What is total cost this month?"],
           "sql": ["SELECT MEASURE(total_cost) FROM mv_cost_analytics WHERE ..."]
         }
       ]
     }
   }
   ```

### Fix Pattern: Low Repeatability

When the same question produces different SQL:

1. **Add sample query** (most effective for repeatability):
   ```json
   {
     "instructions": {
       "example_question_sqls": [
         {
           "id": "generated_uuid_hex",
           "question": ["What are the top cost contributors?"],
           "sql": ["SELECT * FROM get_top_cost_contributors('7', 'workspace')"]
         }
       ]
     }
   }
   ```

2. **Simplify routing rules** - Remove ambiguity:
   ```
   # BEFORE (ambiguous):
   - cost queries → mv_cost_analytics OR get_cost_summary

   # AFTER (deterministic):
   - "total cost" → mv_cost_analytics (always)
   - "cost breakdown" → get_top_cost_contributors (always)
   ```

3. **Define ambiguous terms** explicitly in instructions:
   ```
   === TERM DEFINITIONS ===
   "top" = highest by total_cost DESC unless otherwise specified
   "recent" = last 7 days
   "underperforming" = below median (use get_underperforming TVF)
   ```

---

## Phase 4: Verification

### Re-Test Protocol

```python
# 1. Wait for propagation
print("Waiting 30s for changes to propagate...")
time.sleep(30)

# 2. Re-test ONLY failing questions
improved = 0
for q in failing_questions:
    result = run_genie_query(SPACE_ID, q["question"])
    evaluation = evaluate_accuracy(result, q)
    
    if evaluation["correct_asset"]:
        improved += 1
        print(f"  FIXED: {q['question'][:50]}")
    else:
        print(f"  STILL FAILING: {q['question'][:50]} (got {evaluation['actual_asset']})")
    time.sleep(12)

print(f"\nImproved: {improved}/{len(failing_questions)}")
```

### When to Stop

| Condition | Action |
|-----------|--------|
| Accuracy ≥ 95% AND Repeatability ≥ 90% | Success - document results |
| Accuracy ≥ 90% after 3 iterations | Acceptable - document remaining issues |
| No improvement after 2 iterations | Root cause may be LLM limitation - document |
| Repeatability < 50% on specific question | May need TVF redesign or question rewording |

---

## Advanced Techniques

### TVF-First Design for Repeatability

The Quality domain achieves 100% repeatability by routing most queries through TVFs rather than metric views.

**Why TVFs improve repeatability:**
- Fixed SQL template (parameterized, not generated)
- Deterministic column selection
- Less ambiguity for the LLM

**Pattern:** For each question type, create a dedicated TVF:
```
"Show failed jobs" → get_failed_jobs(days_back)
"Job failure rate" → get_job_failure_rate(days_back)
"Top failing jobs" → get_top_failing_jobs(days_back, limit)
```

### Cross-Domain Optimization

When optimizing the Unified space (all domains):
1. Optimize each domain independently first
2. Combine optimized instructions
3. Test cross-domain questions specifically
4. Watch for routing conflicts between domains

### Incremental Optimization Sessions

Don't try to fix everything at once:
1. **Session 1:** Fix accuracy (correct asset routing)
2. **Session 2:** Fix repeatability (sample queries, term definitions)
3. **Session 3:** Polish (edge cases, formatting rules)

---

## Production Benchmarks (Feb 2026)

Reference scores from optimization of 5 domains:

| Domain | SQL Gen | Repeatability (Before → After) | Key Technique |
|--------|---------|-------------------------------|---------------|
| **Quality** | 100% | 90% → **100%** (+10%) | TVF-first design |
| **Reliability** | 100% | 70% → 80% (+10%) | Explicit routing rules |
| **Security** | 96% | 47% → 67% (+20%) | Sample queries |
| **Performance** | 96% | 40% → 47% (+7%) | Term definitions |
| **Cost** | 100% | 60% → 85% (+25%) | Asset routing + sample queries |

### Key Learnings

1. **TVF-first design improves repeatability** - Quality domain achieves 100% by routing most queries to TVFs
2. **MV queries have higher variance** - LLM makes different column/grouping choices
3. **Explicit routing rules help** - "For X queries, ALWAYS use Y" reduces ambiguity
4. **Instructions alone can't fix everything** - LLM non-determinism is inherent
5. **Sample queries are most effective for repeatability** - Provides exact SQL template

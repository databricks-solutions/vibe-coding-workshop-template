# Feedback-to-Metadata Mapping

Python implementations for introspective analysis: clustering evaluation failures by systemic root cause, generating metadata change proposals, detecting conflicts, and detecting regressions. Judge `rationale` fields are the primary learning signal.

---

## Phase 3: Introspective Analysis Workflow

### Failure Clustering

After evaluation, cluster failures by systemic root cause:

```python
clusters = cluster_failures(eval_result, metadata_snapshot)
```

Only clusters with >=2 questions qualify as systemic. Single-question failures go to the "long tail" bucket for human review.

### Proposal Generation

For each cluster, generate a metadata change proposal:

```python
proposals = generate_metadata_proposals(clusters, metadata_snapshot)

# Or filter to a single lever (used by orchestrator for per-lever optimization):
proposals = generate_metadata_proposals(clusters, metadata_snapshot, target_lever=1)
```

Each proposal includes:
- `lever`: Which control lever to apply (1-6)
- `change_description`: What to change
- `dual_persistence`: API command + repo file path
- `net_impact`: `(questions_fixed × confidence) - (questions_at_risk × regression_probability)`

### Net Impact Formula

```
net_impact = (questions_fixed × confidence) - (questions_at_risk × regression_probability)
```

Only apply proposals with `net_impact > 0`. Defer negative-impact proposals for human review.

### Conflict Detection & Batching

```python
batches = detect_conflicts_and_batch(proposals)
```

Independent proposals (different levers) can be applied together. Conflicting proposals (same lever) are sequenced into separate batches.

### Incremental Application

Apply ONE failure cluster's proposals per iteration:

1. Choose the highest net-impact batch
2. Apply all proposals in the batch via dual persistence
3. Wait 30 seconds for propagation
4. Full-suite re-benchmark (ALL questions, not just failures)
5. Detect regressions: `detect_regressions(current_metrics, previous_metrics)`
6. If regression detected, revert the last change and try an alternative proposal

---

## SIMBA Judge Alignment (Tier 3)

When judges disagree with human assessments, use `SIMBAAlignmentOptimizer` to progressively improve judge accuracy:

```python
from mlflow.genai import SIMBAAlignmentOptimizer

optimizer = SIMBAAlignmentOptimizer()
aligned_judge = optimizer.align(
    judge=schema_accuracy_judge,
    human_labels=human_feedback_dataset,
)
```

Use Tier 3 when the judges themselves are the bottleneck (low agreement rate with human labels).

---

## Function Implementations

### cluster_failures()

Clusters evaluation failures by systemic root cause. Groups failures that share common patterns (same table, same judge, same error type). Only returns clusters with >=2 questions. Single-question failures go to the "long_tail" bucket.

```python
def cluster_failures(eval_results: dict, metadata_snapshot: dict) -> list:
    """Cluster evaluation failures by systemic root cause.

    Groups failures that share common patterns (same table, same judge,
    same error type). Only returns clusters with >=2 questions.
    Single-question failures go to the "long_tail" bucket.

    Returns:
        list of cluster dicts with: cluster_id, root_cause, question_ids,
        affected_judge, confidence, proposed_lever
    """
    from collections import defaultdict

    failures = []
    results_df = eval_results.get("eval_result")
    if results_df is None:
        return []

    table = results_df.tables.get("eval_results", None)
    if table is None:
        return []

    for _, row in table.iterrows():
        for judge_col in [c for c in table.columns if c.startswith("feedback/")]:
            val = row.get(judge_col, "")
            if "no" in str(val).lower():
                failures.append({
                    "question_id": row.get("inputs/question", "unknown"),
                    "judge": judge_col.replace("feedback/", ""),
                    "rationale": row.get(judge_col.replace("feedback/", "rationale/"), ""),
                })

    pattern_groups = defaultdict(list)
    for f in failures:
        key = (f["judge"], _extract_pattern(f["rationale"]))
        pattern_groups[key].append(f)

    clusters = []
    long_tail = []
    for (judge, pattern), items in pattern_groups.items():
        entry = {
            "cluster_id": f"C{len(clusters)+1:03d}",
            "root_cause": pattern,
            "question_ids": [i["question_id"] for i in items],
            "affected_judge": judge,
            "confidence": min(0.9, 0.5 + 0.1 * len(items)),
        }
        if len(items) >= 2:
            clusters.append(entry)
        else:
            long_tail.append(entry)

    clusters.sort(key=lambda c: len(c["question_ids"]), reverse=True)
    return clusters
```

---

### _extract_pattern()

Extracts a generalizable pattern from a judge rationale.

```python
def _extract_pattern(rationale: str) -> str:
    """Extract a generalizable pattern from a judge rationale."""
    r = rationale.lower()
    if "table" in r and ("wrong" in r or "missing" in r or "incorrect" in r):
        return "wrong_table"
    if "column" in r and ("wrong" in r or "missing" in r):
        return "wrong_column"
    if "aggregation" in r or "measure" in r:
        return "wrong_aggregation"
    if "join" in r:
        return "wrong_join"
    if "filter" in r or "where" in r:
        return "wrong_filter"
    if "asset" in r or "routing" in r:
        return "wrong_asset_routing"
    return "other"
```

---

### generate_metadata_proposals()

Generates metadata change proposals for each failure cluster. Each proposal maps to a specific control lever and includes the exact change to make with dual_persistence paths.

```python
def generate_metadata_proposals(clusters: list, metadata_snapshot: dict, target_lever: int | None = None) -> list:
    """Generate metadata change proposals for each failure cluster.

    Each proposal maps to a specific control lever and includes
    the exact change to make with dual_persistence paths.

    Args:
        clusters: Failure clusters from cluster_failures().
        metadata_snapshot: Current metadata for context.
        target_lever: When provided, only return proposals for this lever (1-6).

    Returns:
        list of proposal dicts with: proposal_id, cluster_id, lever,
        change_description, dual_persistence, confidence, questions_fixed,
        questions_at_risk, net_impact
    """
    proposals = []
    for cluster in clusters:
        lever = _map_to_lever(cluster["root_cause"])
        if target_lever is not None and lever != target_lever:
            continue
        proposal = {
            "proposal_id": f"P{len(proposals)+1:03d}",
            "cluster_id": cluster["cluster_id"],
            "lever": lever,
            "change_description": _describe_fix(cluster),
            "dual_persistence": _dual_persist_paths(cluster),
            "confidence": cluster["confidence"],
            "questions_fixed": len(cluster["question_ids"]),
            "questions_at_risk": 0,
            "net_impact": len(cluster["question_ids"]) * cluster["confidence"],
        }
        proposals.append(proposal)

    proposals.sort(key=lambda p: p["net_impact"], reverse=True)
    return proposals
```

---

### _map_to_lever()

Maps root cause to control lever ID.

```python
def _map_to_lever(root_cause: str) -> int:
    mapping = {
        "wrong_table": 1,
        "wrong_column": 1,
        "wrong_aggregation": 2,
        "wrong_join": 1,
        "wrong_filter": 3,
        "wrong_asset_routing": 6,
        "other": 6,
    }
    return mapping.get(root_cause, 6)
```

---

### _describe_fix()

Describes the fix for a cluster.

```python
def _describe_fix(cluster: dict) -> str:
    return (
        f"Fix {cluster['root_cause']} affecting {len(cluster['question_ids'])} questions. "
        f"Judge: {cluster['affected_judge']}."
    )
```

---

### _dual_persist_paths()

Returns API and repo paths for dual persistence.

```python
def _dual_persist_paths(cluster: dict) -> dict:
    lever = _map_to_lever(cluster["root_cause"])
    paths = {
        1: {"api": "ALTER TABLE ... SET TBLPROPERTIES / ALTER COLUMN ... COMMENT",
            "repo": "gold_layer_design/yaml/{domain}/*.yaml"},
        2: {"api": "CREATE OR REPLACE VIEW ... WITH METRICS",
            "repo": "src/semantic/metric_views/*.yaml"},
        3: {"api": "CREATE OR REPLACE FUNCTION",
            "repo": "src/semantic/tvfs/*.sql"},
        6: {"api": "PATCH /api/2.0/genie/spaces/{space_id}",
            "repo": "src/genie/{domain}_genie_export.json"},
    }
    return paths.get(lever, paths[6])
```

---

### detect_conflicts_and_batch()

Detects conflicting proposals and groups independent ones into batches.

```python
def detect_conflicts_and_batch(proposals: list) -> list:
    """Detect conflicting proposals and group independent ones into batches."""
    batches = []
    used_levers = set()
    current_batch = []

    for p in proposals:
        if p["lever"] in used_levers:
            batches.append(current_batch)
            current_batch = [p]
            used_levers = {p["lever"]}
        else:
            current_batch.append(p)
            used_levers.add(p["lever"])

    if current_batch:
        batches.append(current_batch)
    return batches
```

---

### detect_regressions()

Compares current vs previous iteration metrics to detect regressions. A regression is defined as any judge metric dropping by more than 2 percentage points.

```python
def detect_regressions(current_metrics: dict, previous_metrics: dict) -> list:
    """Compare current vs previous iteration metrics to detect regressions."""
    regressions = []
    for key in current_metrics:
        if key in previous_metrics:
            if current_metrics[key] < previous_metrics[key] - 0.02:
                regressions.append({
                    "metric": key,
                    "previous": previous_metrics[key],
                    "current": current_metrics[key],
                    "delta": current_metrics[key] - previous_metrics[key],
                })
    return regressions
```

---

## Regression Detection Usage

```python
regressions = detect_regressions(current_metrics, previous_metrics)
if regressions:
    print(f"  REGRESSION: {regressions}")
    # Revert last change, try alternative
```

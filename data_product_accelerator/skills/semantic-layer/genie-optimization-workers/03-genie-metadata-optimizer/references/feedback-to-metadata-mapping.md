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
- `asi`: dict with `failure_type`, `blame_set`, `severity`, `counterfactual_fixes`, `ambiguity_detected` from the source cluster

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
        affected_judge, confidence, asi_failure_type, asi_blame_set, asi_counterfactual_fixes
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
        questions_at_risk, net_impact, asi
    """
    proposals = []
    for cluster in clusters:
        lever = _map_to_lever(
            cluster["root_cause"],
            asi_failure_type=cluster.get("asi_failure_type"),
            blame_set=cluster.get("asi_blame_set"),
        )
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

Maps root cause to control lever ID. When ASI failure_type is provided, it takes precedence over keyword-derived root_cause. For repeatability_issue, routing depends on blame_set (TABLE/MV/None → 1, TVF → 6).

```python
def _map_to_lever(root_cause: str, asi_failure_type: str = None, blame_set: str = None) -> int:
    ft = asi_failure_type or root_cause
    if ft == "repeatability_issue":
        if blame_set == "TVF":
            return 6
        return 1
    mapping = {
        "wrong_table": 1,
        "wrong_column": 1,
        "wrong_join": 1,
        "wrong_aggregation": 2,
        "wrong_filter": 3,
        "monitoring_gap": 4,
        "stale_data": 4,
        "data_freshness": 4,
        "ml_feature_missing": 5,
        "model_scoring_error": 5,
        "feature_store_mismatch": 5,
        "wrong_asset_routing": 6,
        "other": 6,
    }
    if asi_failure_type and asi_failure_type in mapping:
        return mapping[asi_failure_type]
    return mapping.get(root_cause, 6)
```

---

### _describe_fix()

Describes the fix for a cluster. Prefers ASI counterfactual_fix when available; for repeatability clusters, generates asset-type-specific recommendations (TABLE/MV/TVF/NONE) via _REPEATABILITY_FIX_BY_ASSET.

```python
def _describe_fix(cluster: dict) -> str:
    asi_fixes = cluster.get("asi_counterfactual_fixes", [])
    if asi_fixes:
        return asi_fixes[0]
    if cluster.get("root_cause") == "repeatability_issue":
        dominant_asset = cluster.get("asi_blame_set") or cluster.get("dominant_asset", "TABLE")
        base = _REPEATABILITY_FIX_BY_ASSET.get(dominant_asset, _REPEATABILITY_FIX_BY_ASSET["TABLE"])
        return f"{base} (affects {len(cluster['question_ids'])} questions)"
    return (
        f"Fix {cluster['root_cause']} affecting {len(cluster['question_ids'])} questions. "
        f"Judge: {cluster['affected_judge']}."
    )
```

---

### _dual_persist_paths()

Returns API and repo paths for dual persistence. Supports levers 1-6.

```python
def _dual_persist_paths(cluster: dict) -> dict:
    lever = _map_to_lever(
        cluster["root_cause"],
        asi_failure_type=cluster.get("asi_failure_type"),
        blame_set=cluster.get("asi_blame_set"),
    )
    paths = {
        1: {"api": "ALTER TABLE ... SET TBLPROPERTIES / ALTER COLUMN ... COMMENT",
            "repo": "gold_layer_design/yaml/{domain}/*.yaml"},
        2: {"api": "CREATE OR REPLACE VIEW ... WITH METRICS",
            "repo": "src/semantic/metric_views/*.yaml"},
        3: {"api": "CREATE OR REPLACE FUNCTION",
            "repo": "src/semantic/tvfs/*.sql"},
        4: {"api": "ALTER TABLE ... SET TBLPROPERTIES (monitoring config)",
            "repo": "src/monitoring/{domain}_monitors.yaml"},
        5: {"api": "ALTER TABLE ... SET TBLPROPERTIES (ML feature metadata)",
            "repo": "src/ml/{domain}_feature_tables.yaml"},
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

---

## Per-Lever Proposal Examples

Concrete examples of what proposals should look like for each lever. The orchestrator
iterates levers 1-5 in priority order; each lever targets a specific metadata surface.

### Lever 1: UC Table & Column Metadata

```python
{
    "proposal_id": "L1_001",
    "cluster_id": "wrong_aggregation_booking_analytics",
    "lever": 1,
    "change_description": "Add column comment to booking_analytics_metrics.total_bookings clarifying it counts confirmed bookings only (excludes cancellations)",
    "patch_type": "add_column_description",
    "target_object": "catalog.schema.booking_analytics_metrics",
    "target_column": "total_bookings",
    "dual_persistence": {
        "api": "ALTER TABLE catalog.schema.booking_analytics_metrics ALTER COLUMN total_bookings COMMENT '...'",
        "repo": "src/semantic/table_comments/booking_analytics_metrics.yml"
    },
    "risk_level": "low",
    "estimated_impact": 3
}
```

### Lever 2: Metric View Metadata

```python
{
    "proposal_id": "L2_001",
    "cluster_id": "missing_metric_revenue_per_night",
    "lever": 2,
    "change_description": "Add 'revenue_per_night' measure to wanderbricks_metrics metric view with formula total_revenue/total_nights",
    "patch_type": "add_mv_measure",
    "target_object": "wanderbricks_metrics",
    "dual_persistence": {
        "api": "CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML ...",
        "repo": "src/semantic/metric_views/wanderbricks_metrics.yml"
    },
    "risk_level": "medium",
    "estimated_impact": 5
}
```

### Lever 3: TVF Parameter Metadata

```python
{
    "proposal_id": "L3_001",
    "cluster_id": "wrong_date_filter_tvf_params",
    "lever": 3,
    "change_description": "Update TVF get_booking_stats parameter comment for date_from to specify 'ISO 8601 format, defaults to 30 days ago if omitted'",
    "patch_type": "add_tvf_parameter",
    "target_object": "get_booking_stats",
    "dual_persistence": {
        "api": "ALTER FUNCTION catalog.schema.get_booking_stats ...",
        "repo": "src/semantic/tvfs/get_booking_stats.sql"
    },
    "risk_level": "low",
    "estimated_impact": 2
}
```

### Lever 4: Monitoring Table Integration

```python
{
    "proposal_id": "L4_001",
    "cluster_id": "missing_anomaly_context",
    "lever": 4,
    "change_description": "Add monitoring_alerts table as trusted asset for anomaly detection queries",
    "patch_type": "add_table",
    "target_object": "catalog.schema.monitoring_alerts",
    "dual_persistence": {
        "api": "PATCH /api/2.0/genie/spaces/{space_id} (add data_asset)",
        "repo": "src/semantic/genie_configs/trusted_assets.yml"
    },
    "risk_level": "medium",
    "estimated_impact": 4
}
```

### Lever 5: ML Table Integration

```python
{
    "proposal_id": "L5_001",
    "cluster_id": "missing_prediction_context",
    "lever": 5,
    "change_description": "Add ml_booking_predictions table as trusted asset for forecast queries",
    "patch_type": "add_table",
    "target_object": "catalog.schema.ml_booking_predictions",
    "dual_persistence": {
        "api": "PATCH /api/2.0/genie/spaces/{space_id} (add data_asset)",
        "repo": "src/semantic/genie_configs/trusted_assets.yml"
    },
    "risk_level": "medium",
    "estimated_impact": 3
}
```

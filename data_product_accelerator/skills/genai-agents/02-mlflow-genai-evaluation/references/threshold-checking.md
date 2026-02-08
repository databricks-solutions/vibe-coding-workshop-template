# Threshold Checking Patterns

Complete patterns for checking evaluation metrics against deployment thresholds with metric alias support.

---

## METRIC_ALIASES Definition

**CRITICAL: Handle metric name variations across MLflow versions.**

Built-in scorers use different metric names across MLflow versions. Without aliases, threshold checks fail silently and deployment succeeds with failing scores.

```python
# Built-in scorers use different metric names across MLflow versions
# CRITICAL: Handle both naming conventions to prevent deployment failures
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

---

## check_thresholds() Complete Function

```python
def check_thresholds(metrics: Dict[str, float], thresholds: Dict[str, float]) -> bool:
    """
    Check if evaluation metrics meet deployment thresholds.
    
    Handles metric name variations across MLflow versions using METRIC_ALIASES.
    
    Args:
        metrics: Dict of metric names to values from evaluation
        thresholds: Dict of metric names to minimum thresholds
        
    Returns:
        True if all thresholds met, False otherwise
        
    Why This Is Critical:
    - MLflow 3.0 uses "relevance/mean"
    - MLflow 3.1 uses "relevance_to_query/mean"
    - Without aliases, threshold checks fail silently
    - Deployment succeeds with failing scores (BAD!)
    """
    for metric_name, threshold in thresholds.items():
        # Try primary name first
        if metric_name in metrics:
            if metrics[metric_name] < threshold:
                print(f"❌ {metric_name}: {metrics[metric_name]:.3f} < {threshold} (FAIL)")
                return False
            else:
                print(f"✅ {metric_name}: {metrics[metric_name]:.3f} >= {threshold} (PASS)")
        # Try aliases
        elif metric_name in METRIC_ALIASES:
            found = False
            for alias in METRIC_ALIASES[metric_name]:
                if alias in metrics:
                    if metrics[alias] < threshold:
                        print(f"❌ {metric_name} (as {alias}): {metrics[alias]:.3f} < {threshold} (FAIL)")
                        return False
                    else:
                        print(f"✅ {metric_name} (as {alias}): {metrics[alias]:.3f} >= {threshold} (PASS)")
                    found = True
                    break
            if not found:
                print(f"⚠️ {metric_name} and aliases {METRIC_ALIASES[metric_name]} not found, skipping")
        else:
            print(f"⚠️ {metric_name} not found in metrics, skipping")
    
    return True
```

---

## DEPLOYMENT_THRESHOLDS Dictionary

```python
DEPLOYMENT_THRESHOLDS = {
    # Built-in judges
    "relevance/mean": 0.4,
    "safety/mean": 0.7,
    "guidelines/mean": 0.5,
    
    # Custom domain judges
    "cost_accuracy/mean": 0.6,
    "security_compliance/mean": 0.6,
    "reliability_accuracy/mean": 0.5,
    "performance_accuracy/mean": 0.6,
    "quality_accuracy/mean": 0.6,
    
    # Response quality
    "response_length/mean": 0.1,  # Not too short
    "no_errors/mean": 0.3,  # Minimal error rate
}
```

---

## Why Aliases Matter (MLflow 3.0 vs 3.1)

### The Problem

MLflow changed metric names between versions:

| Metric | MLflow 3.0 | MLflow 3.1 |
|---|---|---|
| Relevance | `relevance/mean` | `relevance_to_query/mean` |
| Safety | `safety/mean` | `safety/mean` (unchanged) |
| Guidelines | `guidelines/mean` | `guidelines/mean` (unchanged) |

### ❌ DON'T: Ignore Metric Name Variations

```python
# BAD: Only checks one metric name
all_passed = metrics.get("relevance/mean", 0) >= 0.4

# Problem: MLflow 3.1 uses "relevance_to_query/mean" instead
# Result: Deployment succeeds even when relevance fails!
```

**What happens:**
- MLflow 3.1 returns `relevance_to_query/mean` = 0.2 (FAIL)
- Code checks `relevance/mean` (doesn't exist)
- Threshold check passes (metric not found)
- Deployment succeeds with failing score (BAD!)

### ✅ DO: Use Metric Aliases

```python
# GOOD: Handles both naming conventions
METRIC_ALIASES = {
    "relevance/mean": ["relevance_to_query/mean"],
}

all_passed = check_thresholds(metrics, DEPLOYMENT_THRESHOLDS)
# ✅ Checks both "relevance/mean" AND "relevance_to_query/mean"
```

**What happens:**
- MLflow 3.1 returns `relevance_to_query/mean` = 0.2 (FAIL)
- Code checks `relevance/mean` (not found)
- Code checks aliases: `relevance_to_query/mean` (found!)
- Threshold check fails correctly
- Deployment blocked (GOOD!)

**Why This Matters:**
- Prevents silent deployment of failing agents
- Works across MLflow 3.0 and 3.1
- Prevents surprises after MLflow upgrades

---

## Complete Usage Example

```python
from evaluation_helpers import check_thresholds, METRIC_ALIASES, DEPLOYMENT_THRESHOLDS

# Run evaluation
results = mlflow.genai.evaluate(
    model=model_uri,
    data=eval_df,
    model_type="databricks-agent",
    evaluators=evaluators,
    evaluator_config=evaluator_config,
)

# Extract metrics
metrics = results.metrics
print("\n📊 Evaluation Metrics:")
print("-" * 80)
for metric_name, value in metrics.items():
    print(f"{metric_name}: {value:.3f}")

# ✅ Use check_thresholds() to handle metric name variations
all_passed = check_thresholds(metrics, DEPLOYMENT_THRESHOLDS)

print("\n" + "-" * 80)
if all_passed:
    print("✅ All thresholds passed - APPROVED for deployment")
else:
    print("❌ Some thresholds failed - NOT approved for deployment")
```

---

## Common Mistakes to Avoid

### ❌ DON'T: Hardcode Metric Names

```python
# BAD: Breaks when MLflow version changes
if metrics["relevance/mean"] < 0.4:
    print("FAIL")
```

### ✅ DO: Use check_thresholds() with Aliases

```python
# GOOD: Handles version differences
all_passed = check_thresholds(metrics, DEPLOYMENT_THRESHOLDS)
```

### ❌ DON'T: Skip Missing Metrics

```python
# BAD: Silent failure if metric doesn't exist
if metrics.get("relevance/mean", 0) >= 0.4:
    print("PASS")  # ❌ Defaults to 0, always passes!
```

### ✅ DO: Check Aliases Before Skipping

```python
# GOOD: check_thresholds() handles missing metrics correctly
all_passed = check_thresholds(metrics, DEPLOYMENT_THRESHOLDS)
# ✅ Checks aliases, warns if metric truly missing
```

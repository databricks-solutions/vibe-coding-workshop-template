# MLflow Experiment Patterns

## Pattern Origin

**Date:** December 2025 (Updated: January 14, 2026 - v4.0)  
**Source:** Production ML pipeline implementation with 25 models across 5 domains  
**Impact:** 96% inference success rate (23/24 models), 93% reduction in debugging time

---

## Critical Rule 0: Pin Package Versions Across All ML Pipelines

```yaml
# ✅ CORRECT: Pin MLflow to SAME version in training AND inference
# resources/ml/ml_training_pipeline.yml
environments:
  - environment_key: default
    spec:
      environment_version: "4"
      dependencies:
        - "mlflow==3.7.0"        # Pin exact version
        - "scikit-learn>=1.3.0"
        - "xgboost>=2.0.0"

# resources/ml/ml_inference_pipeline.yml
environments:
  - environment_key: ml_inference
    spec:
      environment_version: "4"
      dependencies:
        - "mlflow==3.7.0"        # MUST match training version
        - "scikit-learn>=1.3.0"
        - "xgboost>=2.0.0"       # Required for XGBoost models
        - "databricks-feature-engineering"
```

**Warnings you'll see if versions mismatch:**
```
WARNING mlflow.utils.requirements_utils: Detected one or more mismatches 
between the model's dependencies and the current Python environment:
 - mlflow (current: 3.8.1, required: mlflow==3.7.0)

WARNING mlflow.pyfunc: Calling `spark_udf()` with `env_manager="local"` 
does not recreate the same environment that was used during training
```

**Why pinning matters:**
- Models are serialized with specific MLflow version metadata
- Inference deserialization must match training serialization
- `fe.score_batch()` uses `spark_udf()` internally, which checks versions
- Serverless environments can't use `env_manager="conda"` (too slow/unsupported)

---

## Critical Rule 1: Experiment Path - ALWAYS Use `/Shared/`

```python
# ✅ CORRECT: /Shared/ path always works
experiment_name = f"/Shared/{project}_ml_{model_name}"
mlflow.set_experiment(experiment_name)

# ❌ WRONG: User path requires parent folder to exist (will fail silently)
experiment_name = f"/Users/{user}/{project}_ml/{model_name}"

# ❌ WRONG: Using spark to get username (may fail in serverless)
user = spark.sql("SELECT current_user()").collect()[0][0]

# ❌ WRONG: Asset Bundle experiment definitions create duplicates with [dev username] prefix
# Never define experiments in resources/ml/ml_experiments.yml
```

**Root Cause:** `/Users/{user}/subfolder/` fails silently if `subfolder` doesn't exist. Falls back to notebook's default "train" experiment without warning. Asset Bundles add `[dev username]` prefix to experiments in dev mode.

**What we tried (all failed):**
1. Dynamic user path → Parent directory doesn't exist
2. Asset Bundle experiments → Duplicates with dev prefix
3. UC Volume artifact_location → Volume created but experiments failed
4. `/Users/{user}/...` → Silent failure, falls back to "train"

**What worked:** `/Shared/{project}_ml_{model_name}` - always exists, no parent folder issues.

---

## Critical Rule 2: Dataset Logging - MUST Be Inside Run Context

```python
# ✅ CORRECT: Inside mlflow.start_run()
with mlflow.start_run(run_name=run_name) as run:
    # Dataset logging MUST be here
    training_df = spark.table(f"{catalog}.{schema}.{table_name}")
    dataset = mlflow.data.from_spark(
        df=training_df, 
        table_name=f"{catalog}.{schema}.{table_name}",
        version="latest"
    )
    mlflow.log_input(dataset, context="training")
    print(f"✓ Dataset logged: {table_name}")
    
    # Then log params, metrics, model...
    mlflow.log_params({...})
    mlflow.log_metrics({...})
    mlflow.xgboost.log_model(...)

# ❌ WRONG: Outside run context - won't associate with run
dataset = mlflow.data.from_spark(...)
mlflow.log_input(dataset)  # Dataset won't appear in UI!
with mlflow.start_run(run_name=run_name) as run:
    # Dataset logged above won't show in this run!
```

**Root Cause:** MLflow associates artifacts with the *active* run. If called outside `start_run()`, there's no run to associate with.

---

## Critical Rule 3: Helper Functions - ALWAYS Inline

```python
# ✅ CORRECT: Inline helpers in each notebook
def setup_mlflow_experiment(model_name: str) -> str:
    """
    Inlined helper - module imports don't work in Asset Bundle notebooks.
    
    CRITICAL: Do not move this to a shared module!
    """
    experiment_name = f"/Shared/{project}_ml_{model_name}"
    try:
        experiment = mlflow.set_experiment(experiment_name)
        print(f"✓ Experiment: {experiment_name}")
        return experiment_name
    except Exception as e:
        print(f"❌ Experiment setup failed: {e}")
        return None

# ❌ WRONG: Import from shared module - causes ModuleNotFoundError
from {project}_ml.utils.mlflow_setup import setup_mlflow_experiment

# ❌ WRONG: Import from relative path
from ..utils.mlflow_helpers import setup_mlflow_experiment

# ❌ WRONG: Use %run (doesn't work in deployed notebooks)
%run ./utils/mlflow_setup
```

**Root Cause:** Asset Bundle notebooks can't reliably import from local modules due to path resolution issues in serverless environments. Even pure Python files fail to import in this context.

**What we tried:**
1. Created `src/{project}_ml/utils/mlflow_setup.py` → `ModuleNotFoundError`
2. Created `src/{project}_ml/utils/mlflow_helpers.py` → Same error
3. Tried relative imports → Failed
4. Tried sys.path manipulation → Failed

**What worked:** Copy helper functions into each training script (code duplication is acceptable here).

---

## Critical Rule 4: Notebook Exit - ALWAYS Signal Success

```python
def main():
    try:
        # ... training code ...
        
        print("✓ Training completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # ✅ REQUIRED: Signal failure with message
        dbutils.notebook.exit(f"FAILED: {str(e)}")
    
    # ✅ REQUIRED: Signal success to Databricks
    dbutils.notebook.exit("SUCCESS")

# ❌ WRONG: No exit signal - job may show SUCCESS even on failure
def main():
    # ... training code ...
    print("Done!")  # Job status unclear - no dbutils.notebook.exit()
    
# ❌ WRONG: spark.stop() prevents exit signal
def main():
    try:
        # ... training code ...
    finally:
        spark.stop()  # ❌ This will prevent dbutils.notebook.exit() from working!
```

**Root Cause:** Databricks jobs need explicit exit signals. Without `dbutils.notebook.exit()`, the job may show SUCCESS even when code throws exceptions or fails silently.

---

## Standard Training Pipeline Structure

```python
# Databricks notebook source
"""
{Model Name} Training Pipeline

Trains a {model_type} model for {use_case}.
Uses {algorithm} with MLflow 3.1+ best practices.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
import mlflow
from mlflow.models import infer_signature
import pandas as pd
import numpy as np
from xgboost import XGBRegressor  # or XGBClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

# =============================================================================
# MLflow Configuration (at module level)
# =============================================================================
mlflow.set_registry_uri("databricks-uc")

# =============================================================================
# INLINE HELPER FUNCTIONS (do not import - copy to each script)
# =============================================================================
def setup_mlflow_experiment(model_name: str) -> str:
    """Set up MLflow experiment using /Shared/ path."""
    print("\n" + "="*80)
    print(f"Setting up MLflow Experiment: {model_name}")
    print("="*80)
    
    experiment_name = f"/Shared/{project}_ml_{model_name}"
    
    try:
        experiment = mlflow.set_experiment(experiment_name)
        print(f"✓ Experiment set: {experiment_name}")
        print(f"  Experiment ID: {experiment.experiment_id}")
        return experiment_name
    except Exception as e:
        print(f"❌ Experiment setup failed: {e}")
        return None


def log_training_dataset(spark, catalog: str, schema: str, table_name: str) -> bool:
    """Log training dataset for MLflow lineage. MUST be inside mlflow.start_run()."""
    full_table_name = f"{catalog}.{schema}.{table_name}"
    try:
        print(f"  Logging dataset: {full_table_name}")
        training_df = spark.table(full_table_name)
        dataset = mlflow.data.from_spark(
            df=training_df, 
            table_name=full_table_name,
            version="latest"
        )
        mlflow.log_input(dataset, context="training")
        print(f"✓ Dataset logged: {full_table_name}")
        return True
    except Exception as e:
        print(f"⚠️  Dataset logging failed: {e}")
        return False


def get_run_name(model_name: str, algorithm: str, version: str = "v1") -> str:
    """Generate descriptive run name for MLflow tracking."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{model_name}_{algorithm}_{version}_{timestamp}"


def get_standard_tags(model_name: str, domain: str, model_type: str, 
                      algorithm: str, use_case: str, training_table: str,
                      feature_store_enabled: bool = False) -> dict:
    """Get standard MLflow run tags for consistent organization."""
    return {
        "project": "{project}",
        "domain": domain,
        "model_name": model_name,
        "model_type": model_type,  # "regression" or "classification"
        "algorithm": algorithm,     # "xgboost", "gradient_boosting"
        "layer": "ml",
        "team": "data_science",
        "use_case": use_case,
        "feature_store_enabled": str(feature_store_enabled).lower(),
        "training_data": training_table
    }


def get_parameters():
    """Get job parameters from dbutils widgets (NEVER use argparse)."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    model_name = dbutils.widgets.get("model_name")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    print(f"Model Name: {model_name}")
    
    return catalog, gold_schema, feature_schema, model_name


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    """Main training pipeline."""
    
    catalog, gold_schema, feature_schema, model_name = get_parameters()
    
    spark = SparkSession.builder.appName(f"{model_name} Training").getOrCreate()
    
    # Disable autolog to control what's logged
    mlflow.autolog(disable=True)
    
    # Setup experiment
    experiment_name = setup_mlflow_experiment(model_name)
    
    try:
        # Your training logic here...
        
        print("✓ Training completed successfully!")
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {str(e)}")
        print(traceback.format_exc())
        dbutils.notebook.exit(f"FAILED: {str(e)}")
    
    # Signal success (REQUIRED)
    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()
```

---

## Common Experiment Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| Experiment shows as "train" | `/Users/` path failed silently | Use `/Shared/{project}_ml_{model_name}` |
| Dataset not in LoggedModel view | `log_input()` outside run context | Move inside `mlflow.start_run()` |
| Duplicate experiments with `[dev username]` prefix | Asset Bundle experiment definitions | Remove experiments from Asset Bundle YAML |
| `Parent directory does not exist` | User experiment path missing folder | Use `/Shared/` path instead |
| `ModuleNotFoundError: No module named 'src'` | Serverless path resolution | Add `sys.path` setup block to notebook |
| `ModuleNotFoundError` for helpers | Import from local module | Inline all helper functions in each script |

---

## MLflow Setup Checklist

- [ ] Use `/Shared/{project}_ml_{model_name}` experiment path
- [ ] Do NOT define experiments in Asset Bundle
- [ ] Inline ALL helper functions (no module imports)
- [ ] Add `mlflow.autolog(disable=True)` before custom logging
- [ ] Set `mlflow.set_registry_uri("databricks-uc")` at module level
- [ ] Log dataset INSIDE `mlflow.start_run()` context
- [ ] Add `dbutils.notebook.exit("SUCCESS")` at end
- [ ] Do NOT call `spark.stop()` (prevents exit signal)

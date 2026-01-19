# ML Models Implementation Prompt

## 🚀 Quick Start (4-6 hours)

**Goal:** Build production-ready ML pipelines with MLflow 3.1+, Unity Catalog Model Registry, and **Databricks Feature Engineering** for training-serving consistency.

**What You'll Create:**
1. `features/create_feature_tables.py` - Feature tables in Unity Catalog
2. `{domain}/train_{model_name}.py` - Training pipelines with Feature Engineering
3. `inference/batch_inference_all_models.py` - Batch scoring with `fe.score_batch`
4. Asset Bundle jobs for orchestration

**Fast Track:**
```bash
# 1. Create Feature Tables
databricks bundle run ml_feature_pipeline_job -t dev

# 2. Train all models (parallel)
databricks bundle run ml_training_pipeline_job -t dev

# 3. Run batch inference
databricks bundle run ml_inference_pipeline_job -t dev
```

---

## ⚠️ 10 Non-Negotiable Rules

| # | Rule | Pattern | Why It Fails Otherwise |
|---|------|---------|------------------------|
| 1 | **Feature Engineering** | `FeatureLookup` + `create_training_set` + `fe.log_model` | Feature skew between training and inference |
| 2 | **Experiment Path** | `/Shared/{project}_ml_{model_name}` | `/Users/...` fails silently if subfolder doesn't exist |
| 3 | **Dataset Logging** | Inside `mlflow.start_run()` context | Won't associate with run, invisible in UI |
| 4 | **Helper Functions** | ALWAYS inline (no imports) | `ModuleNotFoundError` in serverless |
| 5 | **Exit Signal** | `dbutils.notebook.exit("SUCCESS")` | Job status unclear, may show SUCCESS on failure |
| 6 | **UC Signature** | BOTH input AND output | Unity Catalog rejects models without output spec |
| 7 | **Data Types** | Cast DECIMAL → DOUBLE before training | MLflow signatures don't support DecimalType |
| 8 | **Label Types** | Cast to INT (classification) or DOUBLE (regression) | Type mismatch in model output |
| 9 | **Lookup Keys** | Match Feature Table primary keys EXACTLY | `Unable to find feature` errors |
| 10 | **Inference** | Use `fe.score_batch` NOT manual feature joins | Automatic feature retrieval ensures consistency |

---

## 📋 Your Requirements (Fill These In First)

### Project Context
- **Project Name:** _________________ (e.g., health_monitor)
- **Gold Schema:** _________________ (e.g., my_project_gold)
- **Feature Schema:** _________________ (e.g., my_project_features)
- **Catalog:** _________________ (e.g., my_catalog)

### Feature Tables

| Feature Table | Primary Keys | Features | Source Tables |
|---------------|--------------|----------|---------------|
| cost_features | workspace_id, usage_date | daily_dbu, daily_cost, avg_dbu_7d | fact_usage |
| security_features | user_id, event_date | event_count, failed_auth_count | fact_audit_logs |
| performance_features | warehouse_id, query_date | query_count, avg_duration_ms | fact_query_history |
| ___________ | ___________ | ___________ | ___________ |

### Model Inventory

| Model Name | Type | Algorithm | Label Column | Label Type | Feature Table |
|------------|------|-----------|--------------|------------|---------------|
| budget_forecaster | Regression | GradientBoosting | daily_cost | DOUBLE | cost_features |
| cost_anomaly_detector | Anomaly | IsolationForest | (unsupervised) | N/A | cost_features |
| job_failure_predictor | Classification | XGBoost | prev_day_failed | INT | reliability_features |
| ___________ | ___________ | ___________ | ___________ | ___________ | ___________ |

### Label Type Reference

| Model Type | Label Casting | Example |
|------------|---------------|---------|
| Regression | `.cast("double")` or `.astype('float64')` | `daily_cost`, `p99_duration_ms` |
| Classification | `.cast("int")` or `.astype(int)` | `is_anomaly`, `prev_day_failed`, `schema_change_risk` |
| Anomaly Detection | N/A (unsupervised) | No label column |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Gold Layer                              │
│   (fact_tables, dim_tables - source for feature engineering)    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Feature Tables (Unity Catalog)                      │
│  ┌───────────────────┐ ┌──────────────────┐ ┌─────────────────┐ │
│  │ cost_features     │ │ security_features│ │ performance_    │ │
│  │ PK: workspace_id, │ │ PK: user_id,     │ │   features      │ │
│  │     usage_date    │ │     event_date   │ │ PK: warehouse_id│ │
│  └───────────────────┘ └──────────────────┘ │     query_date  │ │
│                                             └─────────────────┘ │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Training Pipelines                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FeatureLookup → create_training_set → train → fe.log_model ││
│  │  (Embeds feature metadata for inference consistency)        ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│             Unity Catalog Model Registry (MLflow 3.1+)           │
│         catalog.{feature_schema}.{model_name}                    │
│         (Model + Feature Lookup Metadata embedded)               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Inference Layer                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  fe.score_batch(model_uri, df_with_lookup_keys_only)     │   │
│  │  → Automatically retrieves features from Feature Tables  │   │
│  │  → Guarantees training-serving consistency               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
src/{project}_ml/
├── features/
│   └── create_feature_tables.py     # Feature table creation
├── cost/
│   ├── train_budget_forecaster.py
│   ├── train_cost_anomaly_detector.py
│   └── train_chargeback_attribution.py
├── security/
│   └── train_security_threat_detector.py
├── performance/
│   └── train_query_performance_forecaster.py
├── reliability/
│   └── train_job_failure_predictor.py
├── quality/
│   └── train_data_drift_detector.py
├── inference/
│   └── batch_inference_all_models.py  # Uses fe.score_batch
└── README.md

resources/ml/
├── ml_feature_pipeline_job.yml       # Feature table creation
├── ml_training_pipeline_job.yml      # Training orchestrator
└── ml_inference_pipeline_job.yml     # Batch inference
```

---

## Step 1: Feature Table Creation

### Feature Engineering Pattern

```python
# Databricks notebook source
"""
Feature Tables Setup

Creates feature tables in Unity Catalog for ML model training.
Uses Databricks Feature Engineering Client with proper primary keys.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from databricks.feature_engineering import FeatureEngineeringClient
from datetime import datetime, timedelta


def get_parameters():
    """Get job parameters from dbutils widgets (NEVER use argparse)."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    
    return catalog, gold_schema, feature_schema


def create_feature_table(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    features_df,
    full_table_name: str,
    primary_keys: list,
    description: str
):
    """
    Create a feature table in Unity Catalog with proper constraints.
    
    ⚠️ CRITICAL: Primary key columns MUST be NOT NULL.
    """
    print(f"\n{'='*80}")
    print(f"Creating feature table: {full_table_name}")
    print(f"Primary Keys: {primary_keys}")
    print(f"{'='*80}")
    
    # Filter out NULL values in primary key columns
    for pk in primary_keys:
        features_df = features_df.filter(F.col(pk).isNotNull())
    
    # Drop existing table for clean recreation
    try:
        spark.sql(f"DROP TABLE IF EXISTS {full_table_name}")
    except Exception as e:
        print(f"⚠ Could not drop existing table: {e}")
    
    # Create feature table
    fe.create_table(
        name=full_table_name,
        primary_keys=primary_keys,
        df=features_df,
        description=description
    )
    
    record_count = features_df.count()
    print(f"✓ Created {full_table_name} with {record_count} records")
    
    return record_count


def compute_cost_features(spark: SparkSession, catalog: str, gold_schema: str):
    """
    Compute cost features aggregated at workspace-date level.
    
    Primary Keys: workspace_id, usage_date
    """
    fact_usage = f"{catalog}.{gold_schema}.fact_usage"
    
    cost_features = (
        spark.table(fact_usage)
        .groupBy("workspace_id", F.to_date("usage_date").alias("usage_date"))
        .agg(
            F.sum("dbus").alias("daily_dbu"),
            F.sum("list_cost").alias("daily_cost"),
            F.count("*").alias("record_count")
        )
    )
    
    # Add rolling aggregations
    window_7d = Window.partitionBy("workspace_id").orderBy("usage_date").rowsBetween(-6, 0)
    window_30d = Window.partitionBy("workspace_id").orderBy("usage_date").rowsBetween(-29, 0)
    
    cost_features = (
        cost_features
        .withColumn("avg_dbu_7d", F.avg("daily_dbu").over(window_7d))
        .withColumn("avg_dbu_30d", F.avg("daily_dbu").over(window_30d))
        .withColumn("dbu_change_pct_1d", 
            (F.col("daily_dbu") - F.lag("daily_dbu", 1).over(
                Window.partitionBy("workspace_id").orderBy("usage_date")
            )) / F.lag("daily_dbu", 1).over(
                Window.partitionBy("workspace_id").orderBy("usage_date")
            ) * 100
        )
        .withColumn("is_weekend", F.dayofweek("usage_date").isin([1, 7]).cast("int"))
        .withColumn("day_of_week", F.dayofweek("usage_date"))
        .fillna(0)
    )
    
    return cost_features


def main():
    """Main entry point for feature table creation."""
    
    catalog, gold_schema, feature_schema = get_parameters()
    
    spark = SparkSession.builder.appName("Feature Tables Setup").getOrCreate()
    fe = FeatureEngineeringClient()
    
    try:
        # Ensure schema exists
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{feature_schema}")
        
        # Create cost features
        cost_features = compute_cost_features(spark, catalog, gold_schema)
        create_feature_table(
            spark, fe, cost_features,
            f"{catalog}.{feature_schema}.cost_features",
            ["workspace_id", "usage_date"],
            "Cost and usage features for ML models"
        )
        
        # Create additional feature tables...
        
        print("\n" + "="*80)
        print("✓ Feature tables created successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        dbutils.notebook.exit(f"FAILED: {str(e)}")
    
    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()
```

---

## Step 2: Model Training with Feature Engineering

### ⚠️ CRITICAL: Pattern A - Using `fe.log_model` with Feature Lookups

**This pattern embeds feature lookup metadata in the model, enabling automatic feature retrieval at inference.**

```python
# Databricks notebook source
"""
{Model Name} Training Pipeline

Uses Databricks Feature Engineering for training-serving consistency.
Features are automatically retrieved at inference via fe.score_batch.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
import mlflow
from mlflow.models.signature import infer_signature
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor  # or appropriate algorithm
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

# =============================================================================
# MLflow Configuration (at module level)
# =============================================================================
mlflow.set_registry_uri("databricks-uc")


# =============================================================================
# INLINE HELPER FUNCTIONS (NEVER import - copy to each script)
# =============================================================================
def setup_mlflow_experiment(model_name: str) -> str:
    """
    Set up MLflow experiment using /Shared/ path.
    
    ⚠️ CRITICAL: Do NOT move this to a shared module!
    ⚠️ NEVER use /Users/{user}/... paths - they fail silently.
    """
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


def get_run_name(model_name: str, algorithm: str, version: str = "v1") -> str:
    """Generate descriptive run name for MLflow tracking."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{model_name}_{algorithm}_{version}_{timestamp}"


def get_standard_tags(model_name: str, domain: str, model_type: str, 
                      algorithm: str, use_case: str, training_table: str) -> dict:
    """Get standard MLflow run tags for consistent organization."""
    return {
        "project": "{project}",
        "domain": domain,
        "model_name": model_name,
        "model_type": model_type,
        "algorithm": algorithm,
        "layer": "ml",
        "use_case": use_case,
        "feature_engineering": "unity_catalog",
        "training_data": training_table
    }


def get_parameters():
    """Get job parameters from dbutils widgets (NEVER use argparse)."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    
    return catalog, gold_schema, feature_schema


# =============================================================================
# FEATURE ENGINEERING: Create Training Set with FeatureLookup
# =============================================================================
def create_training_set_with_features(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    catalog: str,
    gold_schema: str,
    feature_schema: str
):
    """
    Create training set using Unity Catalog Feature Engineering.
    
    ⚠️ CRITICAL RULES:
    1. base_df contains ONLY lookup keys + label column
    2. All features come from FeatureLookup
    3. Label column must be CAST to correct type (INT for classification, DOUBLE for regression)
    4. lookup_key MUST match feature table primary keys EXACTLY
    """
    model_name = "{model_name}"
    feature_table = f"{catalog}.{feature_schema}.cost_features"  # Update per model
    label_column = "daily_cost"  # Update per model
    
    print(f"\n{'='*80}")
    print(f"Creating Training Set for {model_name}")
    print(f"Feature Table: {feature_table}")
    print(f"Label Column: {label_column}")
    print(f"{'='*80}")
    
    # Features to look up (MUST exist in feature table)
    feature_names = [
        "daily_dbu", "avg_dbu_7d", "avg_dbu_30d", 
        "dbu_change_pct_1d", "is_weekend", "day_of_week"
    ]
    
    # Create FeatureLookup
    # ⚠️ lookup_key MUST match feature table primary keys EXACTLY
    feature_lookups = [
        FeatureLookup(
            table_name=feature_table,
            feature_names=feature_names,
            lookup_key=["workspace_id", "usage_date"]  # Must match feature table PKs
        )
    ]
    
    # ⚠️ CRITICAL: base_df has ONLY lookup keys + label
    # ⚠️ CRITICAL: Cast label to correct type (DOUBLE for regression, INT for classification)
    base_df = (
        spark.table(feature_table)
        .select(
            "workspace_id", 
            "usage_date",
            F.col(label_column).cast("double").alias(label_column)  # Cast for regression
        )
        .filter(F.col(label_column).isNotNull())
        .distinct()
    )
    
    record_count = base_df.count()
    print(f"  Base DataFrame records: {record_count}")
    
    if record_count == 0:
        raise ValueError(f"No records found for training! Check {feature_table}")
    
    # Create training set - features are looked up automatically
    training_set = fe.create_training_set(
        df=base_df,
        feature_lookups=feature_lookups,
        label=label_column,
        exclude_columns=["workspace_id", "usage_date"]  # Exclude lookup keys from features
    )
    
    # Load as DataFrame for training
    training_df = training_set.load_df()
    
    print(f"✓ Training set created")
    print(f"  Columns: {training_df.columns}")
    print(f"  Records: {training_df.count()}")
    
    return training_set, training_df, feature_names, label_column


# =============================================================================
# MODEL TRAINING
# =============================================================================
def prepare_and_train(training_df, feature_names, label_column):
    """
    Prepare data and train model.
    
    ⚠️ CRITICAL: Convert all DECIMAL columns to float64 before training.
    MLflow signatures don't support DecimalType.
    """
    print(f"\n{'='*80}")
    print("Preparing and Training Model")
    print(f"{'='*80}")
    
    pdf = training_df.toPandas()
    
    # ⚠️ CRITICAL: Cast all numeric columns to float64 (handles DECIMAL)
    for col in feature_names:
        if col in pdf.columns:
            pdf[col] = pd.to_numeric(pdf[col], errors='coerce')
    pdf = pdf.fillna(0).replace([np.inf, -np.inf], 0)
    
    X = pdf[feature_names].astype('float64')
    y = pdf[label_column].astype('float64')  # DOUBLE for regression
    # For classification: y = pdf[label_column].astype(int)
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"  Training set: {len(X_train)} samples")
    print(f"  Test set: {len(X_test)} samples")
    
    # Train model
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    metrics = {
        "train_rmse": np.sqrt(mean_squared_error(y_train, train_pred)),
        "test_rmse": np.sqrt(mean_squared_error(y_test, test_pred)),
        "train_r2": r2_score(y_train, train_pred),
        "test_r2": r2_score(y_test, test_pred)
    }
    
    hyperparams = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1,
        "num_features": len(feature_names)
    }
    
    print(f"\n  Test RMSE: {metrics['test_rmse']:.4f}")
    print(f"  Test R²: {metrics['test_r2']:.4f}")
    
    return model, metrics, hyperparams, X_train


# =============================================================================
# MODEL LOGGING WITH FEATURE ENGINEERING (CRITICAL)
# =============================================================================
def log_model_with_feature_engineering(
    fe: FeatureEngineeringClient,
    model,
    training_set,
    X_train: pd.DataFrame,
    metrics: dict,
    hyperparams: dict,
    catalog: str,
    feature_schema: str
):
    """
    Log model using fe.log_model for automatic feature retrieval at inference.
    
    ⚠️ CRITICAL: This embeds feature lookup metadata in the model.
    ⚠️ CRITICAL: Must provide input_example AND signature for Unity Catalog.
    """
    model_name = "{model_name}"
    registered_name = f"{catalog}.{feature_schema}.{model_name}"
    
    print(f"\n{'='*80}")
    print(f"Logging Model with Feature Engineering: {registered_name}")
    print(f"{'='*80}")
    
    mlflow.autolog(disable=True)
    
    with mlflow.start_run(run_name=get_run_name(model_name, "gradient_boosting")) as run:
        # Set tags
        mlflow.set_tags(get_standard_tags(
            model_name=model_name,
            domain="{domain}",
            model_type="regression",
            algorithm="gradient_boosting",
            use_case="{use_case}",
            training_table=f"{catalog}.{feature_schema}.cost_features"
        ))
        
        # Log params and metrics
        mlflow.log_params(hyperparams)
        mlflow.log_metrics(metrics)
        
        # ⚠️ CRITICAL: Create input_example and signature (REQUIRED for UC)
        input_example = X_train.head(5).astype('float64')
        sample_predictions = model.predict(input_example)
        signature = infer_signature(input_example, sample_predictions)
        
        # ⚠️ CRITICAL: Use fe.log_model to embed feature lookup metadata
        fe.log_model(
            model=model,
            artifact_path="model",
            flavor=mlflow.sklearn,
            training_set=training_set,  # Embeds feature lookup spec
            registered_model_name=registered_name,
            input_example=input_example,
            signature=signature
        )
        
        print(f"✓ Model logged with Feature Engineering metadata")
        print(f"  Run ID: {run.info.run_id}")
        print(f"  Registered: {registered_name}")
        
        return {
            "run_id": run.info.run_id,
            "model_name": model_name,
            "registered_as": registered_name,
            "metrics": metrics
        }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    """Main training pipeline with Feature Engineering."""
    
    catalog, gold_schema, feature_schema = get_parameters()
    
    spark = SparkSession.builder.appName("{Model Name} Training").getOrCreate()
    fe = FeatureEngineeringClient()
    
    mlflow.autolog(disable=True)
    setup_mlflow_experiment("{model_name}")
    
    try:
        # Create training set with feature lookups
        training_set, training_df, feature_names, label_column = create_training_set_with_features(
            spark, fe, catalog, gold_schema, feature_schema
        )
        
        # Prepare and train model
        model, metrics, hyperparams, X_train = prepare_and_train(
            training_df, feature_names, label_column
        )
        
        # Log model with feature engineering metadata
        result = log_model_with_feature_engineering(
            fe, model, training_set, X_train,
            metrics, hyperparams, catalog, feature_schema
        )
        
        print("\n" + "="*80)
        print("✓ Training completed successfully!")
        print(f"  Model: {result['registered_as']}")
        print(f"  Test R²: {result['metrics']['test_r2']:.4f}")
        print("="*80)
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error: {str(e)}")
        print(traceback.format_exc())
        dbutils.notebook.exit(f"FAILED: {str(e)}")
    
    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()
```

---

## Step 3: Batch Inference with `fe.score_batch`

### ⚠️ CRITICAL: Use `fe.score_batch` for Automatic Feature Retrieval

```python
# Databricks notebook source
"""
Batch Inference Pipeline

Uses fe.score_batch for automatic feature retrieval from Unity Catalog.
Features are looked up using the metadata embedded during fe.log_model.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient
import mlflow
from mlflow import MlflowClient
from datetime import datetime

mlflow.set_registry_uri("databricks-uc")


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    
    return catalog, gold_schema, feature_schema


def load_model_uri(catalog: str, feature_schema: str, model_name: str) -> str:
    """Get latest model version URI from Unity Catalog."""
    full_model_name = f"{catalog}.{feature_schema}.{model_name}"
    client = MlflowClient()
    
    versions = client.search_model_versions(f"name='{full_model_name}'")
    if not versions:
        raise ValueError(f"No model versions found: {full_model_name}")
    
    latest = max(versions, key=lambda v: int(v.version))
    model_uri = f"models:/{full_model_name}/{latest.version}"
    
    print(f"  Model: {full_model_name}")
    print(f"  Version: {latest.version}")
    print(f"  URI: {model_uri}")
    
    return model_uri


def score_with_feature_engineering(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    model_uri: str,
    scoring_df,
    output_table: str,
    model_name: str
):
    """
    Score batch data using fe.score_batch.
    
    ⚠️ CRITICAL: scoring_df should contain ONLY lookup keys.
    Features are automatically retrieved from Feature Tables.
    """
    print(f"\n{'='*80}")
    print(f"Scoring with fe.score_batch")
    print(f"{'='*80}")
    
    record_count = scoring_df.count()
    print(f"  Input records: {record_count}")
    
    # ⚠️ fe.score_batch automatically retrieves features using embedded metadata
    predictions_df = fe.score_batch(
        model_uri=model_uri,
        df=scoring_df  # Contains only lookup keys
    )
    
    # Add metadata
    predictions_df = (
        predictions_df
        .withColumn("model_name", F.lit(model_name))
        .withColumn("model_uri", F.lit(model_uri))
        .withColumn("scored_at", F.current_timestamp())
    )
    
    # Save predictions
    predictions_df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .saveAsTable(output_table)
    
    saved_count = spark.table(output_table).count()
    print(f"✓ Saved {saved_count} predictions to {output_table}")
    
    return saved_count


def run_inference_for_model(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    catalog: str,
    feature_schema: str,
    model_name: str,
    feature_table: str,
    lookup_keys: list
):
    """Run inference for a single model."""
    print(f"\n{'='*80}")
    print(f"Running Inference: {model_name}")
    print(f"{'='*80}")
    
    try:
        # Load model URI
        model_uri = load_model_uri(catalog, feature_schema, model_name)
        
        # ⚠️ CRITICAL: Select ONLY lookup keys for scoring
        scoring_df = spark.table(feature_table).select(*lookup_keys).distinct()
        
        # Score with fe.score_batch
        output_table = f"{catalog}.{feature_schema}.{model_name}_predictions"
        count = score_with_feature_engineering(
            spark, fe, model_uri, scoring_df, output_table, model_name
        )
        
        return {"status": "SUCCESS", "model": model_name, "records": count}
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"status": "FAILED", "model": model_name, "error": str(e)}


def main():
    """Main batch inference pipeline."""
    
    catalog, gold_schema, feature_schema = get_parameters()
    
    spark = SparkSession.builder.appName("Batch Inference").getOrCreate()
    fe = FeatureEngineeringClient()
    
    # Define models to score
    models = [
        {
            "name": "budget_forecaster",
            "feature_table": f"{catalog}.{feature_schema}.cost_features",
            "lookup_keys": ["workspace_id", "usage_date"]
        },
        {
            "name": "cost_anomaly_detector",
            "feature_table": f"{catalog}.{feature_schema}.cost_features",
            "lookup_keys": ["workspace_id", "usage_date"]
        },
        # Add more models...
    ]
    
    results = []
    for model_config in models:
        result = run_inference_for_model(
            spark, fe, catalog, feature_schema,
            model_config["name"],
            model_config["feature_table"],
            model_config["lookup_keys"]
        )
        results.append(result)
    
    # Summary
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    
    print("\n" + "="*80)
    print(f"BATCH INFERENCE COMPLETE")
    print(f"  Success: {success}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")
    print("="*80)
    
    if failed > 0:
        failed_models = [r["model"] for r in results if r["status"] == "FAILED"]
        dbutils.notebook.exit(f"PARTIAL_FAILURE: {failed_models}")
    
    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()
```

---

## Step 4: Asset Bundle Jobs

### Feature Pipeline Job

```yaml
resources:
  jobs:
    ml_feature_pipeline_job:
      name: "[${bundle.target}] ML Feature Pipeline"
      description: "Creates and updates feature tables in Unity Catalog"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "databricks-feature-engineering>=0.6.0"
      
      tasks:
        - task_key: create_feature_tables
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_ml/features/create_feature_tables.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              feature_schema: ${var.feature_schema}
          timeout_seconds: 3600
      
      tags:
        environment: ${bundle.target}
        layer: ml
        job_type: feature_engineering
```

### Training Pipeline Job

```yaml
resources:
  jobs:
    ml_training_pipeline_job:
      name: "[${bundle.target}] ML Training Pipeline"
      description: "Trains all ML models with Feature Engineering"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "mlflow>=3.1"
              - "databricks-feature-engineering>=0.6.0"
              - "scikit-learn>=1.3.0"
              - "xgboost>=2.0.0"
      
      tasks:
        # Feature Engineering models (parallel)
        - task_key: train_budget_forecaster
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_ml/cost/train_budget_forecaster.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              feature_schema: ${var.feature_schema}
          timeout_seconds: 3600
        
        - task_key: train_cost_anomaly_detector
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_ml/cost/train_cost_anomaly_detector.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              feature_schema: ${var.feature_schema}
          timeout_seconds: 3600
        
        # Add more models...
      
      timeout_seconds: 14400  # 4 hours
      
      tags:
        environment: ${bundle.target}
        layer: ml
        job_type: training
```

### Inference Pipeline Job

```yaml
resources:
  jobs:
    ml_inference_pipeline_job:
      name: "[${bundle.target}] ML Inference Pipeline"
      description: "Batch inference using fe.score_batch"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "mlflow>=3.1"
              - "databricks-feature-engineering>=0.6.0"
      
      tasks:
        - task_key: batch_inference
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_ml/inference/batch_inference_all_models.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              feature_schema: ${var.feature_schema}
          timeout_seconds: 7200
      
      # Schedule: Daily after Gold layer refresh
      schedule:
        quartz_cron_expression: "0 0 5 * * ?"
        timezone_id: "America/Los_Angeles"
        pause_status: PAUSED
      
      tags:
        environment: ${bundle.target}
        layer: ml
        job_type: inference
```

---

## Validation Checklists

### Feature Table Checklist
- [ ] Primary keys defined and NOT NULL
- [ ] All columns verified against Gold layer schema
- [ ] Feature table has descriptive description
- [ ] Rolling window aggregations use proper Window specs
- [ ] NULL values filtered before table creation

### Training Pipeline Checklist
- [ ] Uses `FeatureLookup` for feature retrieval
- [ ] `base_df` has ONLY lookup keys + label column
- [ ] `lookup_key` matches feature table primary keys EXACTLY
- [ ] Label column CAST to correct type (INT/DOUBLE)
- [ ] All features CAST to float64 before training
- [ ] `fe.log_model` used (NOT `mlflow.sklearn.log_model`)
- [ ] `input_example` provided
- [ ] `signature` includes BOTH input AND output
- [ ] `training_set` passed to `fe.log_model`
- [ ] Experiment uses `/Shared/` path
- [ ] All helper functions inlined
- [ ] `dbutils.notebook.exit()` called

### Inference Pipeline Checklist
- [ ] Uses `fe.score_batch` for automatic feature retrieval
- [ ] Scoring DataFrame has ONLY lookup keys
- [ ] Model URI points to latest version
- [ ] Predictions saved with metadata columns
- [ ] Error handling with proper exit signals

---

## Common Errors and Solutions

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Unable to find feature` | lookup_key doesn't match feature table PK | Verify lookup_key matches feature table primary keys |
| `MlflowException: Model signature contains only inputs` | Missing output in signature | Add `model.predict(sample_input)` to `infer_signature` |
| `DecimalType not supported` | DECIMAL columns in input_example | Cast to float64: `X.astype('float64')` |
| `Incompatible input types` | Type mismatch at inference | Use `fe.score_batch` instead of manual preprocessing |
| `Column 'X' cannot be resolved` | Column doesn't exist in feature table | Verify column names against feature table schema |
| `ModuleNotFoundError` | Import from local module | Inline ALL helper functions |
| `Experiment shows as "train"` | `/Users/` path failed silently | Use `/Shared/` experiment path |
| `DataFrame contains column names that match` | Column conflict in FeatureLookup | Remove conflicting columns from base_df |

---

## References

### Feature Engineering
- [Unity Catalog Feature Engineering](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/index.html)
- [FeatureLookup API](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/feature-tables-uc.html)
- [fe.score_batch for Inference](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/feature-tables-uc.html#score-batch)

### MLflow
- [MLflow 3.1 Overview](https://learn.microsoft.com/en-us/azure/databricks/mlflow/mlflow-3-install)
- [Unity Catalog Model Registry](https://learn.microsoft.com/en-us/azure/databricks/machine-learning/manage-model-lifecycle/)
- [Model Signatures](https://mlflow.org/docs/latest/models.html#model-signature)

### Cursor Rules
- [MLflow and ML Models Patterns](../../.cursor/rules/ml/27-mlflow-mlmodels-patterns.mdc)
- [Databricks Asset Bundles](../../.cursor/rules/common/02-databricks-asset-bundles.mdc)

---

## Time Estimates

| Task | Duration |
|------|----------|
| Feature Tables Setup | 2-3 hours |
| First Model (with FE) | 3-4 hours |
| Additional Models (each) | 1-2 hours |
| Batch Inference Pipeline | 2-3 hours |
| Asset Bundle Configuration | 1 hour |
| **Total (5 models)** | **10-16 hours** |


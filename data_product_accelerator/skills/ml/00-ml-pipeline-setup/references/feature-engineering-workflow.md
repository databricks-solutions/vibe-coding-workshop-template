# Feature Engineering Workflow

End-to-end workflow for Unity Catalog Feature Engineering: feature table creation with NaN cleaning, training set creation with `FeatureLookup`, model logging with `fe.log_model`, and batch inference with `fe.score_batch`.

---

## Part A: Feature Table Creation

### compute_cost_features() — Example with Window Functions

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def compute_cost_features(spark: SparkSession, catalog: str, gold_schema: str):
    """
    Compute cost features aggregated at workspace-date level.
    
    Primary Keys: workspace_id, usage_date
    Source: Gold layer fact_usage table
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
```

---

### create_feature_table() — With NaN/Inf Cleaning at Source and DOUBLE Casting

**CRITICAL: NaN/Inf MUST be cleaned at the feature table level, NOT at training time.**  
sklearn models (`GradientBoostingRegressor`, etc.) crash at inference via `fe.score_batch` because there is no NaN handling step at inference — features are retrieved directly from the feature table.

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, IntegerType, LongType, FloatType, 
    DecimalType, ShortType, ByteType
)
from databricks.feature_engineering import FeatureEngineeringClient


def clean_numeric(col_name):
    """Replace NaN, NULL, and Inf with 0.0 for sklearn compatibility."""
    return F.when(
        F.col(col_name).isNull() | F.isnan(F.col(col_name)) |
        (F.col(col_name) == float('inf')) | (F.col(col_name) == float('-inf')),
        F.lit(0.0)
    ).otherwise(F.col(col_name))


def create_feature_table(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    features_df,
    full_table_name: str,
    primary_keys: list,
    description: str
):
    """
    Create a feature table in Unity Catalog with NaN cleaning and DOUBLE casting.
    
    ⚠️ CRITICAL: Primary key columns MUST be NOT NULL.
    ⚠️ CRITICAL: All numeric columns are cast to DOUBLE and NaN/Inf cleaned.
    """
    print(f"\n{'='*80}")
    print(f"Creating feature table: {full_table_name}")
    print(f"Primary Keys: {primary_keys}")
    print(f"{'='*80}")
    
    # Step 1: Filter out NULL values in primary key columns
    for pk in primary_keys:
        features_df = features_df.filter(F.col(pk).isNotNull())
    
    # Step 2: Cast ALL numeric types to DOUBLE (MLflow signatures reject DecimalType)
    numeric_types = (IntegerType, LongType, FloatType, DecimalType, ShortType, ByteType)
    cast_cols = []
    
    for field in features_df.schema.fields:
        if field.name not in primary_keys and isinstance(field.dataType, numeric_types):
            features_df = features_df.withColumn(
                field.name,
                F.coalesce(F.col(field.name).cast("double"), F.lit(0.0))
            )
            cast_cols.append(field.name)
    
    # Step 3: Clean NaN/Inf for existing DOUBLE columns (not already cast above)
    for field in features_df.schema.fields:
        if isinstance(field.dataType, DoubleType) and field.name not in cast_cols:
            features_df = features_df.withColumn(field.name, clean_numeric(field.name))
    
    print(f"  Cast {len(cast_cols)} columns to DOUBLE")
    print(f"  Cleaned NaN/Inf→0.0 for sklearn compatibility")
    
    # Step 4: Drop existing table for clean recreation
    try:
        spark.sql(f"DROP TABLE IF EXISTS {full_table_name}")
    except Exception as e:
        print(f"⚠ Could not drop existing table: {e}")
    
    # Step 5: Create feature table
    fe.create_table(
        name=full_table_name,
        primary_keys=primary_keys,
        df=features_df,
        description=description
    )
    
    record_count = features_df.count()
    print(f"✓ Created {full_table_name} with {record_count} records")
    
    return record_count
```

---

### Main Entry Point for Feature Table Creation

```python
def get_parameters():
    """Get job parameters from dbutils widgets (NEVER use argparse)."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    
    return catalog, gold_schema, feature_schema


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
        
        # Create additional feature tables here...
        # security_features = compute_security_features(spark, catalog, gold_schema)
        # create_feature_table(spark, fe, security_features, ...)
        
        print("\n" + "="*80)
        print("✓ Feature tables created successfully!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        dbutils.notebook.exit(f"FAILED: {str(e)}")
    
    dbutils.notebook.exit("SUCCESS")
```

---

## Part B: Training Set Creation with FeatureLookup

### create_training_set_with_features() — Full Function

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup


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
    2. All features come from FeatureLookup (not hardcoded in base_df)
    3. Label column must be CAST to correct type (INT for classification, DOUBLE for regression)
    4. lookup_key MUST match feature table primary keys EXACTLY
    """
    model_name = "{model_name}"  # Replace per model
    feature_table = f"{catalog}.{feature_schema}.cost_features"  # Replace per model
    label_column = "daily_cost"  # Replace per model
    
    print(f"\n{'='*80}")
    print(f"Creating Training Set for {model_name}")
    print(f"Feature Table: {feature_table}")
    print(f"Label Column: {label_column}")
    print(f"{'='*80}")
    
    # -----------------------------------------------------------------------
    # Step 1: Define features to look up (MUST exist in feature table)
    # -----------------------------------------------------------------------
    feature_names = [
        "daily_dbu", "avg_dbu_7d", "avg_dbu_30d", 
        "dbu_change_pct_1d", "is_weekend", "day_of_week"
    ]
    
    # -----------------------------------------------------------------------
    # Step 2: Create FeatureLookup
    # ⚠️ lookup_key MUST match feature table primary keys EXACTLY
    # -----------------------------------------------------------------------
    feature_lookups = [
        FeatureLookup(
            table_name=feature_table,
            feature_names=feature_names,
            lookup_key=["workspace_id", "usage_date"]  # Must match feature table PKs
        )
    ]
    
    # -----------------------------------------------------------------------
    # Step 3: Build base_df with ONLY lookup keys + label
    # ⚠️ CRITICAL: Cast label to correct type
    #   Regression:     .cast("double")
    #   Classification: .cast("int")
    #   Anomaly:        label=None in create_training_set
    # -----------------------------------------------------------------------
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
    
    # -----------------------------------------------------------------------
    # Step 4: Create training set — features are looked up automatically
    # ⚠️ exclude_columns removes lookup keys from feature set
    # -----------------------------------------------------------------------
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
```

### FeatureLookup Configuration Patterns

```python
# Single primary key
FeatureLookup(
    table_name=f"{catalog}.{feature_schema}.property_features",
    feature_names=["bedrooms", "base_price", "bookings_30d"],
    lookup_key="property_id"  # Single key
)

# Composite primary key (time-series features)
FeatureLookup(
    table_name=f"{catalog}.{feature_schema}.engagement_features",
    feature_names=["view_count", "click_count", "conversion_rate"],
    lookup_key=["property_id", "engagement_date"]  # Composite key
)
```

### base_df Rules

```python
# ✅ CORRECT: base_df has ONLY lookup keys + label
base_df = spark.table(feature_table).select(
    "workspace_id",      # Lookup key 1
    "usage_date",        # Lookup key 2
    F.col("daily_cost").cast("double").alias("daily_cost")  # Label (cast)
)

# ❌ WRONG: base_df includes feature columns (will conflict with FeatureLookup)
base_df = spark.table(feature_table).select(
    "workspace_id", "usage_date",
    "daily_dbu",         # ❌ This will conflict with FeatureLookup!
    "daily_cost"
)
```

### exclude_columns Pattern

```python
# Exclude lookup keys from feature set (they shouldn't be features)
training_set = fe.create_training_set(
    df=base_df,
    feature_lookups=feature_lookups,
    label="daily_cost",
    exclude_columns=["workspace_id", "usage_date"]  # Lookup keys excluded
)
```

---

## Part C: Batch Inference with fe.score_batch

### score_with_feature_engineering() — Full Function

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient
import mlflow
from mlflow import MlflowClient


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
    Features are automatically retrieved from Feature Tables using
    the metadata embedded during fe.log_model.
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
    
    # Add metadata columns
    predictions_df = (
        predictions_df
        .withColumn("model_name", F.lit(model_name))
        .withColumn("model_uri", F.lit(model_uri))
        .withColumn("scored_at", F.current_timestamp())
    )
    
    # Save predictions to Delta
    predictions_df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .saveAsTable(output_table)
    
    saved_count = spark.table(output_table).count()
    print(f"✓ Saved {saved_count} predictions to {output_table}")
    
    return saved_count
```

---

### Multi-Model Inference Loop with Partial Failure Handling

```python
def run_inference_for_model(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    catalog: str,
    feature_schema: str,
    model_name: str,
    feature_table: str,
    lookup_keys: list
):
    """Run inference for a single model with error isolation."""
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
    """Main batch inference pipeline with multi-model loop."""
    
    catalog, gold_schema, feature_schema = get_parameters()
    
    spark = SparkSession.builder.appName("Batch Inference").getOrCreate()
    fe = FeatureEngineeringClient()
    
    # Define models to score (derived from requirements-template.md)
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
        # Add more models from your Model Inventory...
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
```

---

## Part D: Feature Store Patterns (Existing Reference)

### Feature Table Creation — timestamp_keys Deprecation

```python
from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()

# ✅ CORRECT: Primary keys without timestamp_keys
fe.create_table(
    name=f"{catalog}.{feature_schema}.property_features",
    primary_keys=["property_id"],  # Single key
    df=property_features_df,
    description="Property-level features for ML models"
)

# ✅ CORRECT: Composite primary key for time-series
fe.create_table(
    name=f"{catalog}.{feature_schema}.engagement_features",
    primary_keys=["property_id", "engagement_date"],  # Composite key
    df=engagement_features_df,
    description="Daily engagement features"
)

# ❌ WRONG: timestamp_keys was removed in newer versions
fe.create_table(
    name=feature_table_name,
    primary_keys=["property_id"],
    timestamp_keys=["feature_date"],  # ❌ Not supported anymore
    df=features_df
)
```

---

### Feature Store Error: Column Conflict

```python
# ❌ WRONG: DataFrame already has columns that FeatureLookup will add
labels_df = (
    base_df
    .withColumn("day_of_week", dayofweek("date"))  # ❌ This exists in engagement_features!
    .withColumn("is_weekend", ...)
)

# ✅ CORRECT: Let Feature Store provide the columns
labels_df = base_df.select("property_id", "engagement_date", "target")
# day_of_week, is_weekend will come from engagement_features via FeatureLookup
```

**Error:** `DataFrame contains column names that match feature output names`

---

### Feature Registry Pattern

```python
class FeatureRegistry:
    """Registry of feature tables and their schemas."""
    
    def get_feature_columns(self, table_name: str, exclude_columns: list = None) -> list:
        """Get feature columns, optionally excluding specific columns."""
        
        config = self.tables.get(table_name)
        if not config:
            raise ValueError(f"Unknown feature table: {table_name}")
        
        columns = config["columns"]
        
        # Always exclude primary keys
        pk_cols = config.get("primary_keys", [])
        
        # Add user-specified exclusions
        exclude = set(pk_cols)
        if exclude_columns:
            exclude.update(exclude_columns)
        
        return [c for c in columns if c not in exclude]

# Usage
registry = FeatureRegistry()

# ✅ CORRECT: Exclude label from features
feature_names = registry.get_feature_columns(
    FEATURE_TABLE, 
    exclude_columns=[LABEL_COLUMN]
)

# ❌ WRONG: Get all columns including label
feature_names = registry.get_feature_columns(FEATURE_TABLE)  # Label may be included!
```

---

## Feature Engineering Errors

| Error | Root Cause | Solution |
|-------|------------|----------|
| `Unable to find feature '{column}'` | Feature name mismatch or lookup_key doesn't match PKs | Check column names with `DESCRIBE TABLE` and verify lookup_key matches primary keys exactly |
| `DataFrame contains column names that match feature output names` | Column conflict in FeatureLookup | Remove conflicting columns from base_df — let FeatureLookup provide them |
| `create_training_set() missing required argument` | API signature changed | Verify parameters: `df`, `feature_lookups`, `label` |
| `ValueError: Input X contains NaN` | Feature table has NaN, sklearn can't handle it | Clean NaN/Inf at feature table creation with `clean_numeric()` |
| `Incompatible input types` | Type mismatch at inference | Use `fe.score_batch` instead of manual preprocessing |

---

## Workflow Summary

```
1. Fill requirements template → requirements-template.md
2. Create feature tables      → create_feature_table() with NaN cleaning
3. Create training set        → FeatureLookup + create_training_set
4. Train model                → prepare_and_train() with DOUBLE casting
5. Log model                  → fe.log_model() with output_schema
6. Batch inference             → fe.score_batch() with lookup keys only
```

---

## References

- [Unity Catalog Feature Engineering](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/index.html)
- [FeatureLookup API](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/feature-tables-uc.html)
- [fe.score_batch for Inference](https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/feature-tables-uc.html#score-batch)
- [Data Quality Patterns](data-quality-patterns.md) — NaN handling, label binarization
- [Model Registry](model-registry.md) — output_schema patterns by model type

# Databricks notebook source
"""
{Model Name} Training Pipeline — TEMPLATE

╔══════════════════════════════════════════════════════════════════════╗
║  COPY THIS FILE for each model and customize:                        ║
║    1. Replace {project}, {model_name}, {domain}, {use_case}         ║
║    2. Set MODEL_TYPE, ALGORITHM, LABEL_COLUMN, FEATURE_TABLE        ║
║    3. Update feature_names list for your model                       ║
║    4. Choose model class (GradientBoostingRegressor, XGBClassifier)  ║
║    5. For classification: uncomment binarization block               ║
║                                                                      ║
║  This template includes ALL production rules from the skill:         ║
║    • output_schema approach (PRIMARY — not infer_signature)          ║
║    • Label binarization for XGBoost classifiers                      ║
║    • Single-class data detection with graceful SKIPPED exit          ║
║    • NaN defense-in-depth at Pandas level (source cleaned in FT)     ║
║    • Dataset logging inside mlflow.start_run()                       ║
║    • All helper functions inlined (no imports)                        ║
║    • dbutils.notebook.exit() exit signals                            ║
║                                                                      ║
║  See: references/requirements-template.md for planning template      ║
║  See: references/model-registry.md for output_schema patterns        ║
║  See: references/data-quality-patterns.md for binarization/NaN       ║
╚══════════════════════════════════════════════════════════════════════╝

Uses Databricks Feature Engineering for training-serving consistency.
Features are automatically retrieved at inference via fe.score_batch.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
import mlflow
from mlflow.types import ColSpec, DataType, Schema
import pandas as pd
import numpy as np
import json
from sklearn.ensemble import GradientBoostingRegressor  # or XGBClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

# =============================================================================
# MLflow Configuration (at module level — BEFORE any MLflow calls)
# =============================================================================
mlflow.set_registry_uri("databricks-uc")

# =============================================================================
# MODEL CONFIGURATION — CUSTOMIZE THESE FOR YOUR MODEL
# =============================================================================
MODEL_TYPE = "regression"          # "regression", "classification", or "anomaly"
ALGORITHM = "gradient_boosting"    # "gradient_boosting", "xgboost", "isolation_forest"
LABEL_COLUMN = "daily_cost"        # Column name of the label in the feature table
FEATURE_TABLE_NAME = "cost_features"  # Feature table name (without catalog.schema prefix)

# --- Classification-only: Binarization settings (uncomment if needed) ---
# THRESHOLD = 0.2                  # Binarization threshold for continuous labels
# BINARIZED_LABEL_COLUMN = "high_failure_rate"  # Name for binarized label

# =============================================================================
# output_schema — Determines how Unity Catalog stores model output type
# ⚠️ This is the PRIMARY approach. infer_signature is an alternative.
# =============================================================================
if MODEL_TYPE == "regression":
    OUTPUT_SCHEMA = Schema([ColSpec(DataType.double)])     # Continuous prediction
elif MODEL_TYPE == "classification":
    OUTPUT_SCHEMA = Schema([ColSpec(DataType.long)])       # Discrete class: 0, 1, 2...
elif MODEL_TYPE == "anomaly":
    OUTPUT_SCHEMA = Schema([ColSpec(DataType.long)])       # -1 (anomaly) or 1 (normal)
else:
    raise ValueError(f"Unknown MODEL_TYPE: {MODEL_TYPE}")


# =============================================================================
# INLINE HELPER FUNCTIONS (NEVER import — copy to each training script)
# ⚠️ Asset Bundle notebooks can't import local modules in serverless.
# =============================================================================
def setup_mlflow_experiment(model_name: str) -> str:
    """
    Set up MLflow experiment using /Shared/ path.

    ⚠️ CRITICAL: Do NOT move this to a shared module!
    ⚠️ NEVER use /Users/{user}/... paths — they fail silently.
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


def log_training_dataset(spark, catalog: str, schema: str, table_name: str) -> bool:
    """
    Log training dataset for MLflow lineage.

    ⚠️ CRITICAL: MUST be called INSIDE mlflow.start_run() context.
    If called outside, dataset won't associate with the run.
    """
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


def get_standard_tags(
    model_name: str, domain: str, model_type: str,
    algorithm: str, use_case: str, training_table: str,
    feature_store_enabled: bool = True
) -> dict:
    """Get standard MLflow run tags for consistent organization."""
    return {
        "project": "{project}",
        "domain": domain,
        "model_name": model_name,
        "model_type": model_type,
        "algorithm": algorithm,
        "layer": "ml",
        "team": "data_science",
        "use_case": use_case,
        "feature_store_enabled": str(feature_store_enabled).lower(),
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
# SINGLE-CLASS CHECK (from data-quality-patterns.md — Rule 8)
# ⚠️ Classifiers CANNOT train when all samples have the same label.
# =============================================================================
def check_label_distribution(training_df, label_column):
    """
    Check if label has multiple classes. Skip training if single-class.

    Returns: (is_valid, distribution_info)

    ⚠️ Call BEFORE training for classification models.
    Gracefully exits with SKIPPED status if single-class.
    """
    label_distribution = training_df.groupBy(label_column).count().collect()

    if len(label_distribution) < 2:
        single_class = label_distribution[0][label_column]
        sample_count = label_distribution[0]["count"]

        msg = (
            f"Single-class data: all {sample_count} samples have "
            f"label={single_class}. Cannot train classifier."
        )
        print(f"⚠️ {msg}")
        return False, msg

    print(f"  Label distribution: {label_distribution}")
    return True, label_distribution


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
    2. All features come from FeatureLookup (not hardcoded in base_df)
    3. Label column must be CAST to correct type (INT for classification, DOUBLE for regression)
    4. lookup_key MUST match feature table primary keys EXACTLY
    """
    feature_table = f"{catalog}.{feature_schema}.{FEATURE_TABLE_NAME}"

    print(f"\n{'='*80}")
    print(f"Creating Training Set for {LABEL_COLUMN}")
    print(f"Feature Table: {feature_table}")
    print(f"Label Column: {LABEL_COLUMN}")
    print(f"{'='*80}")

    # ------------------------------------------------------------------
    # Features to look up (MUST exist in feature table)
    # ⚠️ CUSTOMIZE: Update this list for your model
    # ------------------------------------------------------------------
    feature_names = [
        "daily_dbu", "avg_dbu_7d", "avg_dbu_30d",
        "dbu_change_pct_1d", "is_weekend", "day_of_week"
    ]

    # ------------------------------------------------------------------
    # Create FeatureLookup
    # ⚠️ lookup_key MUST match feature table primary keys EXACTLY
    # ------------------------------------------------------------------
    feature_lookups = [
        FeatureLookup(
            table_name=feature_table,
            feature_names=feature_names,
            lookup_key=["workspace_id", "usage_date"]  # Must match feature table PKs
        )
    ]

    # ------------------------------------------------------------------
    # Build base_df with ONLY lookup keys + label
    # ⚠️ Cast label to correct type:
    #   Regression:     .cast("double")
    #   Classification: .cast("int")
    #   Anomaly:        label=None (no label column)
    # ------------------------------------------------------------------
    if MODEL_TYPE == "anomaly":
        # Unsupervised: base_df has only lookup keys, no label
        base_df = (
            spark.table(feature_table)
            .select("workspace_id", "usage_date")
            .distinct()
        )
        label_for_training_set = None
    elif MODEL_TYPE == "regression":
        base_df = (
            spark.table(feature_table)
            .select(
                "workspace_id",
                "usage_date",
                F.col(LABEL_COLUMN).cast("double").alias(LABEL_COLUMN)
            )
            .filter(F.col(LABEL_COLUMN).isNotNull())
            .distinct()
        )
        label_for_training_set = LABEL_COLUMN
    else:  # classification
        base_df = (
            spark.table(feature_table)
            .select(
                "workspace_id",
                "usage_date",
                F.col(LABEL_COLUMN).cast("int").alias(LABEL_COLUMN)
            )
            .filter(F.col(LABEL_COLUMN).isNotNull())
            .distinct()
        )
        label_for_training_set = LABEL_COLUMN

    # ------------------------------------------------------------------
    # Optional: Binarize continuous labels for classification
    # Uncomment this block if your label is a continuous rate (0-1)
    # and you are using XGBClassifier.
    # See: references/data-quality-patterns.md — Rule 7
    # ------------------------------------------------------------------
    # if MODEL_TYPE == "classification":
    #     base_df = base_df.withColumn(
    #         BINARIZED_LABEL_COLUMN,
    #         F.when(F.col(LABEL_COLUMN) > THRESHOLD, 1).otherwise(0)
    #     )
    #     label_for_training_set = BINARIZED_LABEL_COLUMN
    #     # Exclude the original continuous column from features
    #     exclude_extra = [LABEL_COLUMN]
    # else:
    #     exclude_extra = []

    record_count = base_df.count()
    print(f"  Base DataFrame records: {record_count}")

    if record_count == 0:
        raise ValueError(f"No records found for training! Check {feature_table}")

    # ------------------------------------------------------------------
    # Create training set — features are looked up automatically
    # ⚠️ exclude_columns removes lookup keys (and optionally original label)
    # ------------------------------------------------------------------
    exclude_columns = ["workspace_id", "usage_date"]
    # If using binarization: exclude_columns += exclude_extra

    training_set = fe.create_training_set(
        df=base_df,
        feature_lookups=feature_lookups,
        label=label_for_training_set,
        exclude_columns=exclude_columns
    )

    # Load as DataFrame for training
    training_df = training_set.load_df()

    print(f"✓ Training set created")
    print(f"  Columns: {training_df.columns}")
    print(f"  Records: {training_df.count()}")

    return training_set, training_df, feature_names, label_for_training_set


# =============================================================================
# MODEL TRAINING
# =============================================================================
def prepare_and_train(training_df, feature_names, label_column):
    """
    Prepare data and train model.

    ⚠️ CRITICAL: Convert all DECIMAL columns to float64 before training.
    MLflow signatures don't support DecimalType.

    Defense-in-depth: NaN cleaning also happens here (primary cleaning
    is at feature table source via create_feature_tables_template.py).
    """
    print(f"\n{'='*80}")
    print("Preparing and Training Model")
    print(f"{'='*80}")

    pdf = training_df.toPandas()

    # ------------------------------------------------------------------
    # Cast all feature columns to float64 (handles DECIMAL residuals)
    # ------------------------------------------------------------------
    for col in feature_names:
        if col in pdf.columns:
            pdf[col] = pd.to_numeric(pdf[col], errors='coerce')

    # Defense-in-depth: clean NaN/Inf at Pandas level too
    pdf = pdf.fillna(0).replace([np.inf, -np.inf], 0)

    X = pdf[feature_names].astype('float64')

    # ------------------------------------------------------------------
    # Label preparation (type depends on MODEL_TYPE)
    # ------------------------------------------------------------------
    if label_column is None:
        # Anomaly detection: no label
        y = None
    elif MODEL_TYPE == "regression":
        y = pdf[label_column].astype('float64')
    else:  # classification
        y = pdf[label_column].astype(int)

    # ------------------------------------------------------------------
    # Train/test split
    # ------------------------------------------------------------------
    if y is not None:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        # Anomaly detection: no labels, no split needed
        X_train, X_test = X, X
        y_train, y_test = None, None

    print(f"  Training set: {len(X_train)} samples")
    if X_test is not None:
        print(f"  Test set: {len(X_test)} samples")

    # ------------------------------------------------------------------
    # Train model — CUSTOMIZE the model class and hyperparameters
    # ------------------------------------------------------------------
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    # For classification: model = XGBClassifier(n_estimators=100, max_depth=5, ...)
    # For anomaly:         model = IsolationForest(n_estimators=100, contamination=0.1, ...)

    if y_train is not None:
        model.fit(X_train, y_train)
    else:
        model.fit(X_train)  # Unsupervised

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------
    if y_train is not None:
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        metrics = {
            "train_rmse": float(np.sqrt(mean_squared_error(y_train, train_pred))),
            "test_rmse": float(np.sqrt(mean_squared_error(y_test, test_pred))),
            "train_r2": float(r2_score(y_train, train_pred)),
            "test_r2": float(r2_score(y_test, test_pred))
        }
        print(f"\n  Test RMSE: {metrics['test_rmse']:.4f}")
        print(f"  Test R²: {metrics['test_r2']:.4f}")
    else:
        # Anomaly detection metrics
        predictions = model.predict(X_train)
        n_anomalies = int(sum(predictions == -1))
        metrics = {
            "total_samples": len(X_train),
            "anomalies_detected": n_anomalies,
            "anomaly_rate": float(n_anomalies / len(X_train))
        }
        print(f"\n  Anomalies detected: {n_anomalies}/{len(X_train)}")

    hyperparams = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1,
        "num_features": len(feature_names),
        "model_type": MODEL_TYPE,
        "algorithm": ALGORITHM
    }

    return model, metrics, hyperparams, X_train


# =============================================================================
# MODEL LOGGING WITH FEATURE ENGINEERING (CRITICAL)
# ⚠️ Uses output_schema (PRIMARY approach) — NOT infer_signature.
# =============================================================================
def log_model_with_feature_engineering(
    spark,
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
    ⚠️ Uses output_schema + infer_input_example (PRIMARY approach).

    Alternative: You CAN use infer_signature() with signature= parameter,
    but output_schema + infer_input_example is more reliable per official docs.
    See: references/model-registry.md — "Alternative: Using infer_signature"
    """
    model_name = "{model_name}"  # Replace with actual model name
    registered_name = f"{catalog}.{feature_schema}.{model_name}"

    print(f"\n{'='*80}")
    print(f"Logging Model with Feature Engineering: {registered_name}")
    print(f"{'='*80}")

    mlflow.autolog(disable=True)

    with mlflow.start_run(run_name=get_run_name(model_name, ALGORITHM)) as run:
        # ------------------------------------------------------------------
        # Log training dataset for lineage (MUST be inside start_run)
        # ------------------------------------------------------------------
        log_training_dataset(
            spark, catalog, feature_schema, FEATURE_TABLE_NAME
        )

        # ------------------------------------------------------------------
        # Set tags
        # ------------------------------------------------------------------
        mlflow.set_tags(get_standard_tags(
            model_name=model_name,
            domain="{domain}",          # Replace: "cost", "security", "performance"
            model_type=MODEL_TYPE,
            algorithm=ALGORITHM,
            use_case="{use_case}",      # Replace: "Budget forecasting", etc.
            training_table=f"{catalog}.{feature_schema}.{FEATURE_TABLE_NAME}",
            feature_store_enabled=True
        ))

        # ------------------------------------------------------------------
        # Log params and metrics
        # ------------------------------------------------------------------
        mlflow.log_params(hyperparams)
        mlflow.log_metrics(metrics)

        # ------------------------------------------------------------------
        # ⚠️ CRITICAL: Use fe.log_model with output_schema (PRIMARY)
        # This embeds feature lookup metadata in the model for fe.score_batch
        # ------------------------------------------------------------------
        fe.log_model(
            model=model,
            artifact_path="model",
            flavor=mlflow.sklearn,            # REQUIRED: specify ML flavor
            training_set=training_set,        # Embeds feature lookup spec
            registered_model_name=registered_name,
            infer_input_example=True,         # Automatically infers input schema
            output_schema=OUTPUT_SCHEMA       # REQUIRED for UC (set at top of file)
        )

        print(f"✓ Model logged with Feature Engineering metadata")
        print(f"  Run ID: {run.info.run_id}")
        print(f"  Registered: {registered_name}")
        print(f"  output_schema: {OUTPUT_SCHEMA}")

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

    spark = SparkSession.builder.appName("{model_name} Training").getOrCreate()
    fe = FeatureEngineeringClient()

    # Disable autolog to control exactly what's logged
    mlflow.autolog(disable=True)

    # Setup experiment
    setup_mlflow_experiment("{model_name}")

    try:
        # ------------------------------------------------------------------
        # Step 1: Create training set with feature lookups
        # ------------------------------------------------------------------
        training_set, training_df, feature_names, label_column = \
            create_training_set_with_features(
                spark, fe, catalog, gold_schema, feature_schema
            )

        # ------------------------------------------------------------------
        # Step 2: Single-class check (classification only)
        # Exits gracefully with SKIPPED if all labels are the same
        # ------------------------------------------------------------------
        if MODEL_TYPE == "classification" and label_column is not None:
            is_valid, distribution = check_label_distribution(
                training_df, label_column
            )
            if not is_valid:
                dbutils.notebook.exit(json.dumps({
                    "status": "SKIPPED",
                    "reason": distribution
                }))

        # ------------------------------------------------------------------
        # Step 3: Prepare and train model
        # ------------------------------------------------------------------
        model, metrics, hyperparams, X_train = prepare_and_train(
            training_df, feature_names, label_column
        )

        # ------------------------------------------------------------------
        # Step 4: Log model with feature engineering metadata
        # ------------------------------------------------------------------
        result = log_model_with_feature_engineering(
            spark, fe, model, training_set, X_train,
            metrics, hyperparams, catalog, feature_schema
        )

        print("\n" + "="*80)
        print("✓ Training completed successfully!")
        print(f"  Model: {result['registered_as']}")
        if 'test_r2' in result['metrics']:
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

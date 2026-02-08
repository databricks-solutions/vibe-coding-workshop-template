# Databricks notebook source
"""
Batch Inference Pipeline — TEMPLATE

╔══════════════════════════════════════════════════════════════════════╗
║  COPY THIS FILE into your project and customize:                     ║
║    1. Replace {project} with your project name                       ║
║    2. Update the `models` list in main() with your models            ║
║    3. Package versions MUST match your training pipeline exactly     ║
║                                                                      ║
║  This template includes ALL production rules from the skill:         ║
║    • fe.score_batch as PRIMARY inference method                      ║
║    • Signature-driven preprocessing FALLBACK for non-FE models       ║
║    • Multi-model loop with per-model error isolation                 ║
║    • PARTIAL_FAILURE exit signal (doesn't mask individual errors)    ║
║    • Metadata columns (model_name, model_uri, scored_at)            ║
║    • Pinned package versions (MUST match training)                   ║
║                                                                      ║
║  See: references/feature-engineering-workflow.md for fe.score_batch  ║
║  See: references/model-registry.md for signature preprocessing      ║
╚══════════════════════════════════════════════════════════════════════╝

Uses fe.score_batch for automatic feature retrieval from Unity Catalog.
Features are looked up using the metadata embedded during fe.log_model.

⚠️ PACKAGE VERSIONS: Pin EXACT versions in your Asset Bundle YAML.
   Training and inference MUST use the same package versions.
   Mismatches cause deserialization warnings and potential failures.
   Example: mlflow==3.7.0, scikit-learn==1.3.2, xgboost==2.0.3
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from databricks.feature_engineering import FeatureEngineeringClient
import mlflow
from mlflow import MlflowClient
import pandas as pd
from datetime import datetime

# =============================================================================
# MLflow Configuration (at module level)
# =============================================================================
mlflow.set_registry_uri("databricks-uc")


# =============================================================================
# PARAMETERS (NEVER use argparse — use dbutils.widgets.get)
# =============================================================================
def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")

    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")

    return catalog, gold_schema, feature_schema


# =============================================================================
# MODEL LOADING
# =============================================================================
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


def load_model_and_signature(
    catalog: str, feature_schema: str, model_name: str, model_version: str = "latest"
):
    """
    Load model and extract signature to know exact expected schema.

    Use this for FALLBACK inference (non-Feature-Store models or
    models that need runtime feature computation like TF-IDF/NLP).

    For Feature Store models, use fe.score_batch instead (PRIMARY method).

    See: references/model-registry.md — "Batch Inference: Signature-Driven Preprocessing"
    """
    full_model_name = f"{catalog}.{feature_schema}.{model_name}"

    if model_version == "latest":
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{full_model_name}'")
        if versions:
            latest_version = max(versions, key=lambda v: int(v.version))
            model_uri = f"models:/{full_model_name}/{latest_version.version}"
        else:
            raise Exception(f"No model versions found for {full_model_name}")
    else:
        model_uri = f"models:/{full_model_name}/{model_version}"

    # Load model to get signature
    model = mlflow.pyfunc.load_model(model_uri)
    signature = model.metadata.signature

    print(f"Model Signature:")
    print(f"  Input columns: {[inp.name for inp in signature.inputs]}")
    print(f"  Input types: {[(inp.name, str(inp.type)) for inp in signature.inputs]}")

    return model, model_uri, signature


def prepare_features_for_signature(pdf: pd.DataFrame, signature):
    """
    Prepare features to EXACTLY match model's expected signature.

    ⚠️ FALLBACK METHOD: Use this ONLY for models NOT using Feature Store,
    or for models that need runtime feature computation (TF-IDF, NLP, etc.).

    For Feature Store models, use fe.score_batch instead — it handles
    feature retrieval and type matching automatically.

    CRITICAL: Type mismatches cause inference failures.
    See: references/model-registry.md — "Common Type Conversion Issues"
    """
    expected_cols = {inp.name: str(inp.type) for inp in signature.inputs}

    for col_name, col_type in expected_cols.items():
        if col_name not in pdf.columns:
            print(f"⚠️  Missing column: {col_name}")
            if 'double' in col_type or 'float' in col_type:
                pdf[col_name] = 0.0
            elif 'long' in col_type or 'integer' in col_type:
                pdf[col_name] = 0
            elif 'boolean' in col_type:
                pdf[col_name] = False
            continue

        # Type conversions
        if 'float32' in col_type:
            pdf[col_name] = pdf[col_name].astype('float32')
        elif 'float64' in col_type or 'double' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0.0).astype('float64')
        elif 'bool' in col_type:
            if pdf[col_name].dtype in ['int64', 'float64']:
                pdf[col_name] = pdf[col_name].astype(bool)
        elif 'long' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0).astype('int64')
        elif 'integer' in col_type:
            pdf[col_name] = pd.to_numeric(pdf[col_name], errors='coerce').fillna(0).astype('int32')

    # Select ONLY columns in signature, in signature order
    signature_col_names = [inp.name for inp in signature.inputs]
    pdf_final = pdf[signature_col_names]

    return pdf_final


# =============================================================================
# PRIMARY INFERENCE: fe.score_batch (for Feature Store models)
# =============================================================================
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
    Features are automatically retrieved from Feature Tables
    using the metadata embedded during fe.log_model.
    """
    print(f"\n{'='*80}")
    print(f"Scoring with fe.score_batch: {model_name}")
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


# =============================================================================
# CUSTOM INFERENCE: For TF-IDF/NLP models that need runtime features
# =============================================================================
# ⚠️ For models that need runtime feature computation (e.g., TF-IDF,
# text embeddings, NLP features), fe.score_batch CANNOT compute these
# at inference time. Use manual preprocessing instead:
#
#   1. Load model and signature with load_model_and_signature()
#   2. Compute features manually (same pipeline as training)
#   3. Prepare features with prepare_features_for_signature()
#   4. Call model.predict() directly
#
# See: SKILL.md Rule 15 (Custom Inference)
# See: references/model-registry.md — "Batch Inference: Signature-Driven Preprocessing"
#
# Example:
#   model, model_uri, signature = load_model_and_signature(catalog, feature_schema, model_name)
#   pdf = compute_runtime_features(spark, input_table)  # Your custom logic
#   pdf_prepared = prepare_features_for_signature(pdf, signature)
#   predictions = model.predict(pdf_prepared)
# =============================================================================


# =============================================================================
# PER-MODEL INFERENCE RUNNER (with error isolation)
# =============================================================================
def run_inference_for_model(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    catalog: str,
    feature_schema: str,
    model_name: str,
    feature_table: str,
    lookup_keys: list
):
    """
    Run inference for a single model with error isolation.

    Each model's errors are caught independently so one failure
    doesn't prevent other models from scoring.
    """
    print(f"\n{'='*80}")
    print(f"Running Inference: {model_name}")
    print(f"{'='*80}")

    try:
        # Load model URI
        model_uri = load_model_uri(catalog, feature_schema, model_name)

        # ⚠️ CRITICAL: Select ONLY lookup keys for scoring
        scoring_df = spark.table(feature_table).select(*lookup_keys).distinct()

        # Score with fe.score_batch (PRIMARY method)
        output_table = f"{catalog}.{feature_schema}.{model_name}_predictions"
        count = score_with_feature_engineering(
            spark, fe, model_uri, scoring_df, output_table, model_name
        )

        return {"status": "SUCCESS", "model": model_name, "records": count}

    except Exception as e:
        print(f"❌ Error scoring {model_name}: {str(e)}")
        return {"status": "FAILED", "model": model_name, "error": str(e)}


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    """
    Main batch inference pipeline.

    Scores all models in sequence with per-model error isolation.
    Reports PARTIAL_FAILURE if any models fail.
    """

    catalog, gold_schema, feature_schema = get_parameters()

    spark = SparkSession.builder.appName("{project} Batch Inference").getOrCreate()
    fe = FeatureEngineeringClient()

    # ------------------------------------------------------------------
    # Define models to score
    # ⚠️ CUSTOMIZE: Add your models from requirements-template.md
    # Each entry maps to a model registered in Unity Catalog.
    # ------------------------------------------------------------------
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
        # {
        #     "name": "job_failure_predictor",
        #     "feature_table": f"{catalog}.{feature_schema}.reliability_features",
        #     "lookup_keys": ["job_id", "run_date"]
        # },
    ]

    # ------------------------------------------------------------------
    # Score each model with error isolation
    # ------------------------------------------------------------------
    results = []
    for model_config in models:
        result = run_inference_for_model(
            spark, fe, catalog, feature_schema,
            model_config["name"],
            model_config["feature_table"],
            model_config["lookup_keys"]
        )
        results.append(result)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = sum(1 for r in results if r["status"] == "FAILED")

    print("\n" + "="*80)
    print(f"BATCH INFERENCE COMPLETE")
    print(f"  Success: {success}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")
    for r in results:
        status_icon = "✓" if r["status"] == "SUCCESS" else "❌"
        records = r.get("records", "N/A")
        print(f"  {status_icon} {r['model']}: {r['status']} ({records} records)")
    print("="*80)

    # ------------------------------------------------------------------
    # Exit signals
    # ------------------------------------------------------------------
    if failed > 0:
        failed_models = [r["model"] for r in results if r["status"] == "FAILED"]
        dbutils.notebook.exit(f"PARTIAL_FAILURE: {failed_models}")

    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()

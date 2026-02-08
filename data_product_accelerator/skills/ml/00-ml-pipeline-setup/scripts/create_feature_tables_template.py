# Databricks notebook source
"""
Feature Tables Setup — TEMPLATE

╔══════════════════════════════════════════════════════════════════════╗
║  COPY THIS FILE into your project and customize:                     ║
║    1. Replace {project} with your project name                       ║
║    2. Add compute_*_features() functions for each domain             ║
║    3. Register each feature table in main()                          ║
║                                                                      ║
║  This template includes ALL production rules from the skill:         ║
║    • NaN/Inf cleaning at source (sklearn compatibility)              ║
║    • DOUBLE type casting for ALL numeric columns                     ║
║    • Primary key NULL filtering                                      ║
║    • Schema creation (CREATE SCHEMA IF NOT EXISTS)                   ║
║    • Record count validation                                         ║
║    • Proper exit signals (SUCCESS / FAILED)                          ║
║                                                                      ║
║  See: references/requirements-template.md for planning template      ║
║  See: references/feature-engineering-workflow.md for full docs        ║
║  See: references/data-quality-patterns.md for NaN handling details   ║
╚══════════════════════════════════════════════════════════════════════╝

Creates feature tables in Unity Catalog for ML model training.
Uses Databricks Feature Engineering Client with proper primary keys.

⚠️ CRITICAL: NaN/Inf is cleaned AT SOURCE (not at training time).
   This prevents sklearn inference failures via fe.score_batch.
   XGBoost handles NaN natively, but sklearn does not.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    DoubleType, IntegerType, LongType, FloatType,
    DecimalType, ShortType, ByteType
)
from databricks.feature_engineering import FeatureEngineeringClient
from datetime import datetime, timedelta


# =============================================================================
# INLINE HELPER: clean_numeric (from data-quality-patterns.md)
# ⚠️ CRITICAL: Do NOT move to a shared module — inline in each notebook.
# =============================================================================
def clean_numeric(col_name):
    """
    Replace NaN, NULL, and Inf with 0.0 for sklearn compatibility.

    ⚠️ ROOT CAUSE OF 3 INFERENCE FAILURES (Jan 2026):
    sklearn GradientBoosting* crashes with 'ValueError: Input X contains NaN'
    when feature tables contain NaN. XGBoost handles NaN natively, but sklearn
    does not. Cleaning at the feature table source prevents this at inference.
    """
    return F.when(
        F.col(col_name).isNull() | F.isnan(F.col(col_name)) |
        (F.col(col_name) == float('inf')) | (F.col(col_name) == float('-inf')),
        F.lit(0.0)
    ).otherwise(F.col(col_name))


# =============================================================================
# PARAMETERS (NEVER use argparse — use dbutils.widgets.get)
# =============================================================================
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
# FEATURE TABLE CREATION (with NaN cleaning + DOUBLE casting)
# =============================================================================
def create_feature_table(
    spark: SparkSession,
    fe: FeatureEngineeringClient,
    features_df,
    full_table_name: str,
    primary_keys: list,
    description: str
):
    """
    Create a feature table in Unity Catalog with production-grade data cleaning.

    Steps applied (in order):
      1. Filter NULL primary key rows
      2. Cast ALL non-PK numeric columns to DOUBLE (MLflow rejects DecimalType)
      3. Clean NaN/Inf → 0.0 on ALL DOUBLE columns (sklearn compatibility)
      4. Drop and recreate the table via fe.create_table()
      5. Validate record count

    ⚠️ CRITICAL: Primary key columns MUST be NOT NULL.
    ⚠️ CRITICAL: NaN cleaning happens HERE, not at training time.
    """
    print(f"\n{'='*80}")
    print(f"Creating feature table: {full_table_name}")
    print(f"Primary Keys: {primary_keys}")
    print(f"{'='*80}")

    # ------------------------------------------------------------------
    # Step 1: Filter out NULL values in primary key columns
    # ------------------------------------------------------------------
    initial_count = features_df.count()
    for pk in primary_keys:
        features_df = features_df.filter(F.col(pk).isNotNull())
    filtered_count = features_df.count()
    removed = initial_count - filtered_count
    if removed > 0:
        print(f"  Filtered {removed} rows with NULL primary keys ({initial_count} → {filtered_count})")

    # ------------------------------------------------------------------
    # Step 2: Cast ALL non-PK numeric types to DOUBLE
    # MLflow signatures reject DecimalType, IntegerType, etc.
    # ------------------------------------------------------------------
    numeric_types = (IntegerType, LongType, FloatType, DecimalType, ShortType, ByteType)
    cast_cols = []

    for field in features_df.schema.fields:
        if field.name not in primary_keys and isinstance(field.dataType, numeric_types):
            features_df = features_df.withColumn(
                field.name,
                F.coalesce(F.col(field.name).cast("double"), F.lit(0.0))
            )
            cast_cols.append(field.name)

    # ------------------------------------------------------------------
    # Step 3: Clean NaN/Inf → 0.0 for ALL DOUBLE columns (sklearn compat)
    # ------------------------------------------------------------------
    nan_cleaned = 0
    for field in features_df.schema.fields:
        if isinstance(field.dataType, DoubleType) and field.name not in cast_cols:
            features_df = features_df.withColumn(field.name, clean_numeric(field.name))
            nan_cleaned += 1

    total_cleaned = len(cast_cols) + nan_cleaned
    print(f"  Cast {len(cast_cols)} columns to DOUBLE, cleaned NaN/Inf on {total_cleaned} columns")

    # ------------------------------------------------------------------
    # Step 4: Drop existing table for clean recreation
    # ------------------------------------------------------------------
    try:
        spark.sql(f"DROP TABLE IF EXISTS {full_table_name}")
    except Exception as e:
        print(f"⚠ Could not drop existing table: {e}")

    # ------------------------------------------------------------------
    # Step 5: Create feature table via Feature Engineering Client
    # ------------------------------------------------------------------
    fe.create_table(
        name=full_table_name,
        primary_keys=primary_keys,
        df=features_df,
        description=description
    )

    record_count = features_df.count()
    print(f"✓ Created {full_table_name} with {record_count} records")

    # Validate
    if record_count == 0:
        print(f"⚠️  WARNING: Feature table {full_table_name} has 0 records!")

    return record_count


# =============================================================================
# DOMAIN-SPECIFIC FEATURE ENGINEERING
# Copy and customize for each feature table in your project.
# =============================================================================
def compute_cost_features(spark: SparkSession, catalog: str, gold_schema: str):
    """
    Compute cost features aggregated at workspace-date level.

    Primary Keys: workspace_id, usage_date
    Source: {catalog}.{gold_schema}.fact_usage

    ⚠️ Replace this function body with YOUR domain feature logic.
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    """Main entry point for feature table creation."""

    catalog, gold_schema, feature_schema = get_parameters()

    spark = SparkSession.builder.appName("{project} Feature Tables Setup").getOrCreate()
    fe = FeatureEngineeringClient()

    try:
        # ------------------------------------------------------------------
        # Ensure feature schema exists
        # ------------------------------------------------------------------
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{feature_schema}")
        print(f"✓ Schema verified: {catalog}.{feature_schema}")

        # ------------------------------------------------------------------
        # Create each feature table
        # Add more compute_*_features() → create_feature_table() calls here
        # ------------------------------------------------------------------
        total_records = 0

        # --- Cost features ---
        cost_features = compute_cost_features(spark, catalog, gold_schema)
        count = create_feature_table(
            spark, fe, cost_features,
            f"{catalog}.{feature_schema}.cost_features",
            ["workspace_id", "usage_date"],
            "Cost and usage features for ML models. "
            "Aggregated at workspace-date level with rolling 7d/30d averages."
        )
        total_records += count

        # --- Add more feature tables here ---
        # security_features = compute_security_features(spark, catalog, gold_schema)
        # count = create_feature_table(
        #     spark, fe, security_features,
        #     f"{catalog}.{feature_schema}.security_features",
        #     ["user_id", "event_date"],
        #     "Security audit features for ML models."
        # )
        # total_records += count

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print("\n" + "="*80)
        print(f"✓ Feature tables created successfully!")
        print(f"  Total records across all tables: {total_records}")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        dbutils.notebook.exit(f"FAILED: {str(e)}")

    dbutils.notebook.exit("SUCCESS")


if __name__ == "__main__":
    main()

"""
MLflow Experiment Setup Utility

CRITICAL: This script should be INLINED in each training notebook.
Do NOT import from this file - copy the function into your notebook.

Reason: Asset Bundle notebooks can't reliably import from local modules
due to path resolution issues in serverless environments.
"""

import mlflow
from datetime import datetime


def setup_mlflow_experiment(model_name: str) -> str:
    """
    Set up MLflow experiment using /Shared/ path.
    
    CRITICAL: Always use /Shared/ path, never /Users/ path.
    /Users/ paths fail silently if parent directory doesn't exist.
    
    Args:
        model_name: Name of the model (e.g., "demand_predictor")
        
    Returns:
        Experiment name (e.g., "/Shared/{project}_ml_demand_predictor")
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
    
    CRITICAL: MUST be called inside mlflow.start_run() context.
    If called outside, dataset won't associate with the run.
    
    Args:
        spark: SparkSession
        catalog: Unity Catalog catalog name
        schema: Schema name
        table_name: Table name
        
    Returns:
        True if successful, False otherwise
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
    """
    Generate descriptive run name for MLflow tracking.
    
    Args:
        model_name: Name of the model
        algorithm: Algorithm used (e.g., "xgboost", "gradient_boosting")
        version: Version identifier (default: "v1")
        
    Returns:
        Run name string (e.g., "demand_predictor_xgboost_v1_20250115_143022")
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{model_name}_{algorithm}_{version}_{timestamp}"


def get_standard_tags(
    model_name: str,
    domain: str,
    model_type: str,
    algorithm: str,
    use_case: str,
    training_table: str,
    feature_store_enabled: bool = False
) -> dict:
    """
    Get standard MLflow run tags for consistent organization.
    
    Args:
        model_name: Name of the model
        domain: Domain (e.g., "cost", "performance", "quality")
        model_type: "regression" or "classification"
        algorithm: Algorithm used (e.g., "xgboost")
        use_case: Business use case description
        training_table: Full table name used for training
        feature_store_enabled: Whether Feature Store is used
        
    Returns:
        Dictionary of standard tags
    """
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
    """
    Get job parameters from dbutils widgets.
    
    CRITICAL: NEVER use argparse in Databricks notebooks.
    Use dbutils.widgets.get() instead.
    
    Returns:
        Tuple of (catalog, gold_schema, feature_schema, model_name)
    """
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    feature_schema = dbutils.widgets.get("feature_schema")
    model_name = dbutils.widgets.get("model_name")
    
    print(f"Catalog: {catalog}")
    print(f"Gold Schema: {gold_schema}")
    print(f"Feature Schema: {feature_schema}")
    print(f"Model Name: {model_name}")
    
    return catalog, gold_schema, feature_schema, model_name

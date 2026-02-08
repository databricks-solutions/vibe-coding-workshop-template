# Dataset Lineage Patterns

Complete patterns for linking evaluation datasets to MLflow runs using `mlflow.log_input()` for traceability and audit trails.

## mlflow.log_input() Pattern

```python
import mlflow
from mlflow.data import from_spark
from pyspark.sql import DataFrame

def load_evaluation_dataset_with_lineage() -> DataFrame:
    """
    Load evaluation dataset and link to MLflow run.
    
    CRITICAL: Always use mlflow.log_input() for evaluation datasets.
    """
    # Load dataset from Unity Catalog
    eval_df = spark.table("gold.evaluation.agent_eval_dataset")
    
    # Link dataset to current run
    mlflow.log_input(
        from_spark(eval_df),
        context="evaluation"
    )
    
    return eval_df
```

## from_spark() Usage

```python
from mlflow.data import from_spark
from pyspark.sql import DataFrame

def log_dataset_to_run(df: DataFrame, context: str = "evaluation"):
    """
    Log Spark DataFrame to MLflow run with proper lineage.
    
    Args:
        df: Spark DataFrame
        context: Context for dataset (e.g., "evaluation", "training")
    """
    # Convert Spark DataFrame to MLflow dataset
    dataset = from_spark(
        df,
        path="gold.evaluation.agent_eval_dataset"  # Unity Catalog table path
    )
    
    # Log to current run
    mlflow.log_input(dataset, context=context)
```

## UC Table Schema for Eval Dataset

```sql
-- Create evaluation dataset table in Unity Catalog
CREATE TABLE IF NOT EXISTS gold.evaluation.agent_eval_dataset (
    request STRING NOT NULL COMMENT 'User query/request',
    expected_response STRING COMMENT 'Expected response (optional)',
    domain STRING COMMENT 'Domain context (billing, monitoring, etc.)',
    created_at TIMESTAMP NOT NULL COMMENT 'Dataset creation timestamp',
    version INT COMMENT 'Dataset version number'
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Evaluation dataset for GenAI agent with versioning'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);
```

## Complete load_evaluation_dataset_with_lineage Function

```python
import mlflow
from mlflow.data import from_spark
from pyspark.sql import DataFrame
from typing import Optional

def load_evaluation_dataset_with_lineage(
    table_path: str = "gold.evaluation.agent_eval_dataset",
    version: Optional[int] = None,
    context: str = "evaluation"
) -> DataFrame:
    """
    Load evaluation dataset with MLflow lineage tracking.
    
    Args:
        table_path: Unity Catalog table path
        version: Optional dataset version (uses latest if None)
        context: Context for dataset logging
    
    Returns:
        Spark DataFrame with dataset logged to MLflow run
    """
    # Load dataset
    if version:
        # Load specific version using time travel
        eval_df = spark.read.format("delta").option(
            "versionAsOf", version
        ).table(table_path)
    else:
        # Load latest version
        eval_df = spark.table(table_path)
    
    # Log dataset to current MLflow run
    try:
        dataset = from_spark(
            eval_df,
            path=table_path
        )
        
        mlflow.log_input(dataset, context=context)
        
        # Log dataset metadata
        mlflow.log_param("eval_dataset_path", table_path)
        if version:
            mlflow.log_param("eval_dataset_version", version)
        
        # Log dataset statistics
        row_count = eval_df.count()
        mlflow.log_metric("eval_dataset_rows", row_count)
        
        print(f"Logged evaluation dataset: {table_path} ({row_count} rows)")
        
    except Exception as e:
        print(f"Warning: Failed to log dataset lineage: {str(e)}")
        # Continue even if logging fails
    
    return eval_df
```

## Dataset Versioning Pattern

```python
def load_evaluation_dataset_versioned(
    version: int,
    table_path: str = "gold.evaluation.agent_eval_dataset"
) -> DataFrame:
    """
    Load specific version of evaluation dataset with lineage.
    
    Useful for reproducibility and audit trails.
    """
    # Load versioned dataset
    eval_df = spark.read.format("delta").option(
        "versionAsOf", version
    ).table(table_path)
    
    # Log with version information
    dataset = from_spark(eval_df, path=table_path)
    mlflow.log_input(dataset, context="evaluation")
    mlflow.log_param("eval_dataset_version", version)
    
    return eval_df
```

## Dataset Lineage in Evaluation Runs

```python
def run_evaluation_with_dataset_lineage(
    model_uri: str,
    eval_dataset_path: str
):
    """
    Run evaluation with proper dataset lineage tracking.
    """
    mlflow.set_experiment("/Shared/health_monitor_agent/evaluation")
    
    run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with mlflow.start_run(run_name=run_name):
        # Load and log evaluation dataset
        eval_df = load_evaluation_dataset_with_lineage(
            table_path=eval_dataset_path,
            context="evaluation"
        )
        
        # Run evaluation
        results = mlflow.genai.evaluate(
            model=model_uri,
            data=eval_df,
            model_type="databricks-agent",
            evaluators=evaluators
        )
        
        # Results automatically linked to dataset via run
        return results
```

## Querying Dataset Lineage

```python
def get_evaluation_runs_for_dataset(
    dataset_path: str,
    experiment_path: str = "/Shared/health_monitor_agent/evaluation"
) -> list:
    """
    Query all evaluation runs that used a specific dataset.
    
    Useful for dataset impact analysis.
    """
    runs = mlflow.search_runs(
        experiment_ids=[mlflow.get_experiment_by_name(experiment_path).experiment_id],
        filter_string=f"params.eval_dataset_path = '{dataset_path}'",
        order_by=["start_time DESC"]
    )
    
    return runs
```

## Usage Example

```python
import mlflow
from mlflow.data import from_spark

# In evaluation notebook
mlflow.set_experiment("/Shared/health_monitor_agent/evaluation")

with mlflow.start_run(run_name="eval_pre_deploy_20250206_120000"):
    # Load evaluation dataset
    eval_df = spark.table("gold.evaluation.agent_eval_dataset")
    
    # Link dataset to run (CRITICAL for traceability)
    mlflow.log_input(
        from_spark(eval_df, path="gold.evaluation.agent_eval_dataset"),
        context="evaluation"
    )
    
    # Run evaluation
    results = mlflow.genai.evaluate(
        model="models:/health_monitor_agent/1",
        data=eval_df,
        model_type="databricks-agent",
        evaluators=evaluators
    )
    
    # Dataset is now linked to this evaluation run
    # Can query lineage: "Which runs used this dataset?"
```

## Benefits of Dataset Lineage

1. **Traceability**: Know which dataset version was used for each evaluation
2. **Reproducibility**: Re-run evaluations with exact same dataset
3. **Audit Trail**: Track dataset usage across all runs
4. **Impact Analysis**: Find all runs affected by dataset changes
5. **Compliance**: Required for production ML systems

## Validation Checklist

- [ ] ✅ **`mlflow.log_input()` called for all evaluation datasets**
- [ ] ✅ **`from_spark()` used for Spark DataFrames**
- [ ] ✅ **Context set to "evaluation"**
- [ ] ✅ **Dataset path logged as parameter**
- [ ] ✅ **Dataset version logged (if versioned)**
- [ ] ✅ **Dataset stored in Unity Catalog**

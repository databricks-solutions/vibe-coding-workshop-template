# Trace Archival Patterns

Complete patterns for enabling MLflow trace archival to Unity Catalog Delta tables for production monitoring and analysis.

## enable_databricks_trace_archival() Pattern

```python
import mlflow

def enable_trace_archival(
    catalog: str = "catalog",
    schema: str = "schema",
    table: str = "agent_traces"
):
    """
    Enable trace archival to Unity Catalog Delta table.
    
    Args:
        catalog: Unity Catalog catalog name
        schema: Schema name
        table: Table name for archived traces
    """
    mlflow.enable_databricks_trace_archival(
        catalog=catalog,
        schema=schema,
        table=table
    )
    
    print(f"Trace archival enabled: {catalog}.{schema}.{table}")
```

## Delta Table Schema

```sql
-- Create trace archival table in Unity Catalog
CREATE TABLE IF NOT EXISTS catalog.schema.agent_traces (
    trace_id STRING NOT NULL COMMENT 'MLflow trace ID',
    experiment_id STRING COMMENT 'MLflow experiment ID',
    run_id STRING COMMENT 'MLflow run ID',
    trace_info STRUCT<
        request_id: STRING,
        timestamp: TIMESTAMP,
        status: STRING
    > COMMENT 'Trace metadata',
    spans ARRAY<STRUCT<
        span_id: STRING,
        name: STRING,
        span_type: STRING,
        start_time: TIMESTAMP,
        end_time: TIMESTAMP,
        status: STRING,
        inputs: STRING,
        outputs: STRING,
        tags: MAP<STRING, STRING>,
        metadata: MAP<STRING, STRING>
    >> COMMENT 'Trace spans',
    created_at TIMESTAMP NOT NULL COMMENT 'Archive timestamp'
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Archived MLflow traces for production monitoring'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);
```

## Experiment Configuration

```python
def configure_trace_archival_experiment(
    experiment_name: str = "/Shared/health_monitor_agent/production"
):
    """
    Configure experiment for trace archival.
    
    Args:
        experiment_name: MLflow experiment path
    """
    # Create or get experiment
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(experiment_name)
        else:
            experiment_id = experiment.experiment_id
    except Exception:
        experiment_id = mlflow.create_experiment(experiment_name)
    
    # Enable trace archival for this experiment
    mlflow.set_experiment(experiment_name)
    
    print(f"Trace archival configured for experiment: {experiment_name}")
    return experiment_id
```

## Querying Archived Traces

```python
from pyspark.sql import DataFrame
from datetime import datetime, timedelta

def query_archived_traces(
    start_time: datetime = None,
    end_time: datetime = None,
    trace_table: str = "catalog.schema.agent_traces"
) -> DataFrame:
    """
    Query archived traces from Delta table.
    
    Args:
        start_time: Start time for query (default: 24 hours ago)
        end_time: End time for query (default: now)
        trace_table: Unity Catalog table path
    
    Returns:
        Spark DataFrame with traces
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(days=1)
    if end_time is None:
        end_time = datetime.now()
    
    # Query traces
    traces_df = spark.sql(f"""
        SELECT *
        FROM {trace_table}
        WHERE created_at >= '{start_time.isoformat()}'
          AND created_at <= '{end_time.isoformat()}'
        ORDER BY created_at DESC
    """)
    
    return traces_df
```

## Trace Analysis Patterns

```python
def analyze_trace_errors(
    traces_df: DataFrame,
    trace_table: str = "catalog.schema.agent_traces"
) -> DataFrame:
    """
    Analyze traces for errors.
    
    Returns traces with error status.
    """
    error_traces = spark.sql(f"""
        SELECT 
            trace_id,
            trace_info.request_id,
            trace_info.timestamp,
            trace_info.status,
            spans
        FROM {trace_table}
        WHERE trace_info.status = 'ERROR'
           OR EXISTS(
               SELECT 1 
               FROM UNNEST(spans) AS span
               WHERE span.status = 'ERROR'
           )
        ORDER BY trace_info.timestamp DESC
    """)
    
    return error_traces


def analyze_trace_performance(
    traces_df: DataFrame,
    trace_table: str = "catalog.schema.agent_traces"
) -> DataFrame:
    """
    Analyze trace performance metrics.
    
    Returns performance statistics per trace.
    """
    performance_df = spark.sql(f"""
        SELECT 
            trace_id,
            trace_info.timestamp,
            COUNT(spans) AS span_count,
            SUM(
                UNIX_TIMESTAMP(spans.end_time) - 
                UNIX_TIMESTAMP(spans.start_time)
            ) AS total_duration_ms,
            AVG(
                UNIX_TIMESTAMP(spans.end_time) - 
                UNIX_TIMESTAMP(spans.start_time)
            ) AS avg_span_duration_ms
        FROM {trace_table}
        LATERAL VIEW EXPLODE(spans) AS spans
        GROUP BY trace_id, trace_info.timestamp
        ORDER BY trace_info.timestamp DESC
    """)
    
    return performance_df
```

## Complete Setup Workflow

```python
def setup_trace_archival(
    catalog: str = "catalog",
    schema: str = "schema",
    table: str = "agent_traces",
    experiment_name: str = "/Shared/health_monitor_agent/production"
):
    """
    Complete trace archival setup workflow.
    
    1. Create Delta table (if not exists)
    2. Enable trace archival
    3. Configure experiment
    """
    # Step 1: Create table (run DDL if needed)
    # (Table creation handled separately via SQL)
    
    # Step 2: Enable trace archival
    enable_trace_archival(
        catalog=catalog,
        schema=schema,
        table=table
    )
    
    # Step 3: Configure experiment
    experiment_id = configure_trace_archival_experiment(experiment_name)
    
    print(f"Trace archival setup complete:")
    print(f"  Table: {catalog}.{schema}.{table}")
    print(f"  Experiment: {experiment_name}")
    
    return experiment_id
```

## Usage Example

```python
# Setup trace archival
setup_trace_archival(
    catalog="production",
    schema="monitoring",
    table="agent_traces",
    experiment_name="/Shared/health_monitor_agent/production"
)

# Traces are now automatically archived to:
# production.monitoring.agent_traces

# Query archived traces
traces_df = query_archived_traces(
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)

# Analyze errors
error_traces = analyze_trace_errors(traces_df)

# Analyze performance
performance_df = analyze_trace_performance(traces_df)
```

## Validation Checklist

- [ ] Delta table created with proper schema
- [ ] Trace archival enabled via `enable_databricks_trace_archival()`
- [ ] Experiment configured for archival
- [ ] Query patterns tested
- [ ] Error analysis queries working
- [ ] Performance analysis queries working

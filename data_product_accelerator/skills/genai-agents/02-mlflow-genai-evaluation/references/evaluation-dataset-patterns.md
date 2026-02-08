# Evaluation Dataset Patterns

Complete patterns for creating and loading evaluation datasets for MLflow GenAI evaluation.

---

## Evaluation Dataset Schema

Evaluation datasets define ground truth queries and expected outputs for agent evaluation.

### Schema Structure

```json
[
  {
    "request": "What is the total cost for workspace ABC123 this month?",
    "response": "Optional: Expected response text",
    "context": "Optional: Additional context for evaluation"
  },
  {
    "request": "Show me security compliance issues",
    "response": "Optional: Expected response text"
  }
]
```

**Required Fields:**
- `request`: User query (required)

**Optional Fields:**
- `response`: Expected response text (for correctness evaluation)
- `context`: Additional context for evaluation

---

## Loading from Unity Catalog

```python
import pandas as pd

# Load evaluation dataset from Unity Catalog table
eval_df = spark.table(f"{catalog}.{schema}.evaluation_dataset").toPandas()

# Or load from JSON file
eval_df = pd.read_json("path/to/evaluation_dataset.json")

print(f"✓ Loaded evaluation dataset: {len(eval_df)} queries")
```

---

## Dataset Linking with mlflow.log_input()

**CRITICAL: Link evaluation dataset to MLflow run for reproducibility.**

```python
import mlflow
import pandas as pd

# Load evaluation dataset
eval_df = pd.read_json("path/to/evaluation_dataset.json")

# Create MLflow dataset from pandas DataFrame
eval_dataset = mlflow.data.from_pandas(
    eval_df,
    source="path/to/evaluation_dataset.json",
    name="health_monitor_agent_evaluation_dataset"
)

# Link dataset to run
with mlflow.start_run(run_name=run_name) as run:
    # Log evaluation parameters
    mlflow.log_params({
        "model_uri": model_uri,
        "eval_dataset": "path/to/evaluation_dataset.json",
        "num_queries": len(eval_df),
    })
    
    # ✅ Link dataset to run
    mlflow.log_input(eval_dataset, context="evaluation")
    
    # Run evaluation
    results = mlflow.genai.evaluate(
        model=model_uri,
        data=eval_df,  # Use DataFrame directly
        model_type="databricks-agent",
        evaluators=evaluators,
        evaluator_config=evaluator_config,
    )
```

**Why this matters:**
- Reproducibility: Know exactly which dataset was used
- Lineage: Track dataset versions across evaluations
- Debugging: Compare results across dataset versions

---

## from_spark() Pattern

**Load evaluation dataset from Spark DataFrame:**

```python
import mlflow

# Load from Unity Catalog
eval_df = spark.table(f"{catalog}.{schema}.evaluation_dataset")

# Create MLflow dataset from Spark DataFrame
eval_dataset = mlflow.data.from_spark(
    eval_df,
    source=f"{catalog}.{schema}.evaluation_dataset",
    name="health_monitor_agent_evaluation_dataset"
)

# Link to run
with mlflow.start_run() as run:
    mlflow.log_input(eval_dataset, context="evaluation")
    
    # Convert to pandas for mlflow.genai.evaluate()
    eval_pandas = eval_df.toPandas()
    
    results = mlflow.genai.evaluate(
        model=model_uri,
        data=eval_pandas,
        model_type="databricks-agent",
        evaluators=evaluators,
    )
```

---

## Column Mapping Configuration

**Configure column names in evaluation dataset:**

```python
# Evaluation dataset has custom column names
eval_df = pd.DataFrame({
    "user_query": ["Query 1", "Query 2"],
    "expected_response": ["Response 1", "Response 2"],
})

# Configure column mapping
evaluator_config = {
    "col_mapping": {
        "inputs": "user_query",  # Map to request column
        "output": "expected_response",  # Map to response column
    }
}

results = mlflow.genai.evaluate(
    model=model_uri,
    data=eval_df,
    model_type="databricks-agent",
    evaluators=evaluators,
    evaluator_config=evaluator_config,  # ✅ Column mapping
)
```

**Default column names:**
- `inputs`: `"request"` (user query)
- `output`: `"response"` (agent response)

---

## Viewing Scored Outputs CSV

**Download and analyze per-query evaluation results:**

```python
from mlflow import MlflowClient
import pandas as pd

client = MlflowClient()

# Get latest evaluation run
runs = mlflow.search_runs(
    experiment_ids=[experiment_id],
    filter_string="tags.mlflow.runName LIKE 'eval_pre_deploy_%'",
    order_by=["start_time DESC"],
    max_results=1
)

run_id = runs.iloc[0]['run_id']

# List artifacts
artifacts = client.list_artifacts(run_id)
for artifact in artifacts:
    if "scored_outputs" in artifact.path:
        # Download CSV
        local_path = client.download_artifacts(run_id, artifact.path)
        
        # Read and analyze
        df = pd.read_csv(local_path)
        
        # Columns include:
        # - request: Original query
        # - response: Agent output
        # - relevance: Relevance score
        # - relevance/justification: Why this score
        # - safety: Safety score
        # - guidelines: Guidelines score
        # - cost_accuracy: Custom judge score
        # ... etc ...
        
        print(df[['request', 'relevance', 'safety', 'guidelines']].head())
        
        # Analyze failures
        failed_queries = df[df['relevance'] < 0.4]
        print(f"\n❌ Failed queries: {len(failed_queries)}")
        print(failed_queries[['request', 'relevance', 'relevance/justification']])
```

---

## Complete Evaluation Dataset Example

```python
import mlflow
import pandas as pd
from datetime import datetime

# Load evaluation dataset
eval_df = pd.read_json("path/to/evaluation_dataset.json")
print(f"✓ Loaded evaluation dataset: {len(eval_df)} queries")

# Create MLflow dataset
eval_dataset = mlflow.data.from_pandas(
    eval_df,
    source="path/to/evaluation_dataset.json",
    name="health_monitor_agent_evaluation_dataset"
)

# Set evaluation experiment
mlflow.set_experiment("/Shared/health_monitor_agent_evaluation")

# Run name convention
run_name = f"eval_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Run evaluation with dataset linking
with mlflow.start_run(run_name=run_name) as run:
    # Log evaluation parameters
    mlflow.log_params({
        "model_uri": model_uri,
        "eval_dataset": "path/to/evaluation_dataset.json",
        "num_queries": len(eval_df),
    })
    
    # ✅ Link dataset to run
    mlflow.log_input(eval_dataset, context="evaluation")
    
    # Run evaluation
    results = mlflow.genai.evaluate(
        model=model_uri,
        data=eval_df,
        model_type="databricks-agent",
        evaluators=evaluators,
        evaluator_config={
            "col_mapping": {
                "inputs": "request",  # Column in eval dataset
                "output": "response",  # Column in eval dataset
            }
        },
    )
    
    print(f"✓ Evaluation complete: {run.info.run_id}")
    
    # Extract metrics
    metrics = results.metrics
    print("\n📊 Evaluation Metrics:")
    for metric_name, value in metrics.items():
        print(f"{metric_name}: {value:.3f}")
```

---

## Best Practices

### 1. Version Control Evaluation Datasets

- Store evaluation datasets in Git
- Use descriptive filenames: `evaluation_dataset_v1.json`
- Document dataset changes in commit messages

### 2. Representative Query Selection

- Include diverse query types (cost, security, performance, etc.)
- Include edge cases and error scenarios
- Include both simple and complex queries

### 3. Expected Outputs (Optional)

- Include expected responses for correctness evaluation
- Use for regression testing
- Not required for LLM-as-judge evaluation

### 4. Dataset Size

- Minimum: 10-20 queries for meaningful evaluation
- Recommended: 50-100 queries for comprehensive evaluation
- Production: 100+ queries for thorough validation

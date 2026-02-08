# MLflow Tracing Patterns

## Automatic Tracing with autolog

Enable autolog at module level for automatic tracing:

```python
import mlflow

# At the TOP of your main module
mlflow.langchain.autolog(
    log_models=True,
    log_input_examples=True,
    log_model_signatures=True,
    log_inputs=True
)
```

**Benefits:**
- Automatic tracing of LangChain operations
- Model logging with signatures
- Input/output examples captured
- No manual instrumentation needed

## Manual Tracing with Decorators

Use `@mlflow.trace` for custom functions:

```python
import mlflow

@mlflow.trace(name="my_function", span_type="AGENT")
def my_agent_function(query: str) -> dict:
    """Function is automatically traced."""
    result = process(query)
    return result
```

**Span Types:**

| Span Type | Use For |
|-----------|---------|
| `AGENT` | Agent-level operations |
| `LLM` | LLM calls |
| `TOOL` | Tool invocations |
| `RETRIEVER` | RAG/memory retrieval |
| `CLASSIFIER` | Classification operations |
| `MEMORY` | Memory operations |

## Manual Span Creation

For fine-grained control:

```python
import mlflow

def complex_operation(data):
    with mlflow.start_span(name="outer_operation") as span:
        span.set_inputs({"data": data})
        
        with mlflow.start_span(name="inner_step", span_type="LLM") as inner:
            inner.set_inputs({"prompt": "..."})
            result = llm.invoke(...)
            inner.set_outputs({"response": result})
        
        span.set_outputs({"result": result})
        span.set_attributes({"custom_metric": 0.95})
    
    return result
```

## Trace Tagging

Always tag traces for filtering:

```python
mlflow.update_current_trace(tags={
    "user_id": user_id,
    "session_id": session_id,
    "environment": os.environ.get("ENVIRONMENT", "dev"),
    "domains": ",".join(domains),
    "confidence": str(confidence)
})
```

## Trace Storage in Unity Catalog

Traces can be routed to a specific Unity Catalog Delta table for long-term storage and analysis.

**Reference:** [Unity Catalog Traces](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage)

### Programmatic Trace Storage Configuration

```python
# Databricks notebook source
"""
Configure Unity Catalog trace storage for agent experiment.

Reference: https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage
"""

import mlflow
from databricks.sdk import WorkspaceClient

# Parameters
catalog = dbutils.widgets.get("catalog")
agent_schema = dbutils.widgets.get("agent_schema")

EXPERIMENT_PATH = "/Shared/health_monitor_agent_evaluation"
TRACE_TABLE_NAME = f"{catalog}.{agent_schema}.agent_traces"

# Set experiment
mlflow.set_experiment(EXPERIMENT_PATH)

# Get experiment ID
client = mlflow.MlflowClient()
experiment = client.get_experiment_by_name(EXPERIMENT_PATH)
experiment_id = experiment.experiment_id

# Configure trace storage destination
w = WorkspaceClient()

w.experiments.set_experiment_tag(
    experiment_id=experiment_id,
    key="mlflow.tracing.destination.catalog",
    value=catalog
)

w.experiments.set_experiment_tag(
    experiment_id=experiment_id,
    key="mlflow.tracing.destination.schema",
    value=agent_schema
)

w.experiments.set_experiment_tag(
    experiment_id=experiment_id,
    key="mlflow.tracing.destination.table",
    value="agent_traces"
)

print(f"Trace storage configured: {TRACE_TABLE_NAME}")
```

### Querying Stored Traces

Once configured, traces are stored in the designated Delta table and can be queried with SQL:

```sql
SELECT 
    trace_id,
    span_name,
    span_type,
    start_time,
    end_time,
    inputs,
    outputs
FROM ${catalog}.${agent_schema}.agent_traces
WHERE tags['user_id'] = 'user123'
ORDER BY start_time DESC
LIMIT 100
```

## Viewing Traces in MLflow UI

1. **Navigate to MLflow Experiment:**
   - Go to Experiments tab
   - Select your experiment

2. **View Trace Details:**
   - Click on a run
   - Go to "Traces" tab
   - See span hierarchy and details

3. **Analyze Performance:**
   - View span durations
   - Identify bottlenecks
   - Check input/output data

## Common Patterns

### Agent Tracing

```python
@mlflow.trace(name="agent_predict", span_type="AGENT")
def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    """Agent prediction with automatic tracing."""
    # All operations within this function are traced
    result = self._process(request)
    return result
```

### Tool Invocation Tracing

```python
with mlflow.start_span(name=f"genie_{domain}", span_type="TOOL") as tool_span:
    tool_span.set_inputs({"domain": domain, "query": query})
    
    try:
        result = genie.invoke(query)
        tool_span.set_outputs({"source": "genie", "response": result})
        return success_response
    except Exception as e:
        tool_span.set_attributes({"error": str(e), "fallback": "none"})
        tool_span.set_outputs({"source": "error"})
        return error_response
```

### LLM Call Tracing

```python
with mlflow.start_span(name="llm_call", span_type="LLM") as llm_span:
    llm_span.set_inputs({"prompt": prompt, "temperature": 0.7})
    
    response = llm.invoke(prompt)
    
    llm_span.set_outputs({
        "response": response.content,
        "tokens": response.usage.total_tokens
    })
    
    return response
```

## Best Practices

1. **Use autolog for LangChain:**
   - Enable at module level
   - Automatic instrumentation

2. **Decorate custom functions:**
   - Use `@mlflow.trace` for important functions
   - Specify appropriate span types

3. **Set inputs and outputs:**
   - Always set inputs for spans
   - Set outputs for successful operations
   - Set attributes for metadata

4. **Tag traces:**
   - Add user_id, session_id tags
   - Include environment information
   - Tag with domain/feature identifiers

5. **Handle errors:**
   - Set error attributes in spans
   - Log error details to outputs
   - Maintain trace continuity

## References

- [MLflow Tracing Documentation](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/)
- [MLflow GenAI Concepts](https://docs.databricks.com/aws/en/mlflow3/genai/concepts/)

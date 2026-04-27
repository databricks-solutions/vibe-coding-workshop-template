# Agent Logging Reference

Complete reference for logging GenAI agents to MLflow on Databricks. Covers
code-based logging, LangChain logging, resource declarations, input examples,
pre-deployment validation, and common error resolution.

Official docs: https://docs.databricks.com/aws/en/generative-ai/agent-framework/log-agent

---

## 1. Code-Based Logging (`mlflow.pyfunc.log_model`)

The primary pattern for logging a Python agent that lives in a standalone file:

```python
import mlflow
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksFunction,
    DatabricksGenieSpace,
    DatabricksTable,
    DatabricksSQLWarehouse,
)

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model="/path/to/agent.py",
        input_example={"input": [{"role": "user", "content": "Hello"}]},
        resources=[
            DatabricksServingEndpoint(endpoint_name="my-llm-endpoint"),
            DatabricksVectorSearchIndex(index_name="catalog.schema.my_index"),
        ],
        pip_requirements=[
            "mlflow[databricks]>=3.10.1",
            "databricks-sdk>=0.40.0",
            "openai>=1.17",
        ],
    )
```

### Key parameters

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `artifact_path` | Yes | Subdirectory in MLflow artifacts where the model is stored |
| `python_model` | Yes | Path to agent `.py` file or a `PythonModel` instance |
| `input_example` | Recommended | Sample input for signature inference and documentation |
| `resources` | Recommended | Databricks resource declarations for lineage and deployment |
| `pip_requirements` | Recommended | Python packages needed at inference time |
| `signature` | Avoid for GenAI | Auto-inferred by `ResponsesAgent`/`ChatAgent`; manual overrides cause mismatches |

### `mlflow.models.set_model()` requirement

When `python_model` is a **file path** (not an instance), the file must call
`mlflow.models.set_model()` so MLflow can locate the entry point:

```python
# agent.py
import mlflow
from my_agent import MyAgent

agent = MyAgent()
mlflow.models.set_model(agent)
```

Without this call, `log_model` raises:

```
MlflowException: The specified model file does not define a model object.
Call mlflow.models.set_model() in your model file.
```

---

## 2. LangChain Logging (`mlflow.langchain.log_model`)

For agents built with LangChain or LangGraph:

```python
import mlflow

with mlflow.start_run():
    model_info = mlflow.langchain.log_model(
        lc_model="/path/to/agent.py",
        artifact_path="agent",
        input_example={"input": [{"role": "user", "content": "Hello"}]},
        resources=[
            DatabricksServingEndpoint(endpoint_name="my-llm"),
            DatabricksVectorSearchIndex(index_name="prod.docs.index"),
        ],
        pip_requirements=[
            "mlflow[databricks]>=3.10.1",
            "langchain>=0.3",
            "langgraph>=0.2",
        ],
    )
```

The agent file must also call `mlflow.models.set_model()`:

```python
# langchain_agent.py
import mlflow
from langchain_core.runnables import RunnableSequence

chain = RunnableSequence(...)
mlflow.models.set_model(chain)
```

### LangChain vs pyfunc logging

| Aspect | `mlflow.pyfunc.log_model` | `mlflow.langchain.log_model` |
|--------|---------------------------|------------------------------|
| Agent type | Any `PythonModel` or file | LangChain `Runnable` or file |
| Tracing flavor | `pyfunc` | `langchain` (richer span types) |
| Dependency tracking | Manual `pip_requirements` | Auto-captures LangChain deps |
| Resource declarations | Same `resources` API | Same `resources` API |

---

## 3. Resource Declarations

Resource declarations tell Databricks what external services the agent requires.
They enable automatic permission provisioning during deployment, lineage tracking
in Unity Catalog, and dependency documentation.

### All resource types

```python
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksFunction,
    DatabricksGenieSpace,
    DatabricksTable,
    DatabricksSQLWarehouse,
)

resources = [
    DatabricksServingEndpoint(endpoint_name="my-llm"),
    DatabricksVectorSearchIndex(index_name="catalog.schema.index"),
    DatabricksFunction(function_name="catalog.schema.my_udf"),
    DatabricksGenieSpace(genie_space_id="01abc123def456"),
    DatabricksTable(table_name="catalog.schema.my_table"),
    DatabricksSQLWarehouse(warehouse_id="abc123def456"),
]
```

### Resource declaration rules

1. **Declare every external dependency** — missing resources cause deployment
   failures or runtime permission errors.
2. **Use three-level names** for UC resources (`catalog.schema.object`).
3. **Warehouse resources** are needed if the agent runs SQL queries at inference.
4. **Serving endpoints** include both LLM endpoints and embedding endpoints.
5. **Vector search indexes** require the index name, not the endpoint name.

### What happens without resource declarations

| Scenario | Symptom |
|----------|---------|
| Missing `DatabricksServingEndpoint` | `PermissionDenied` at inference — agent's SP lacks endpoint access |
| Missing `DatabricksVectorSearchIndex` | `NOT_FOUND` or permission error on vector search queries |
| Missing `DatabricksFunction` | UC function calls fail silently or with `PERMISSION_DENIED` |
| Missing `DatabricksTable` | Direct table reads fail at serving time |

---

## 4. Input Example Best Practices

The input example serves three purposes: (1) signature inference, (2) documentation,
and (3) pre-deployment validation.

### Standard GenAI input example

```python
input_example = {
    "input": [
        {"role": "user", "content": "What were total sales last quarter?"}
    ]
}
```

### Multi-turn conversation example

```python
input_example = {
    "input": [
        {"role": "user", "content": "Show me revenue by region"},
        {"role": "assistant", "content": "Here is the breakdown..."},
        {"role": "user", "content": "Now filter to North America only"},
    ]
}
```

### Rules

| Rule | Rationale |
|------|-----------|
| Use `"input"` as the top-level key | Standard for `ResponsesAgent`; `"messages"` causes schema mismatch |
| Include at least one `user` message | Validates the agent handles the minimal case |
| Keep examples short | Large examples slow logging and inflate artifact size |
| Match the schema your agent expects | The example drives signature inference — wrong shape = wrong signature |

---

## 5. Pre-Deployment Validation

Always validate the logged model before deploying to a serving endpoint:

```python
result = mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data={"input": [{"role": "user", "content": "test query"}]},
)
assert result is not None, "Model prediction returned None"
```

### What `mlflow.models.predict` checks

1. **Dependency resolution** — all pip packages install correctly.
2. **Signature compatibility** — input matches the logged signature.
3. **Resource access** — resource declarations are syntactically valid.
4. **Agent initialization** — `set_model()` target loads without errors.

### Validation in CI

```python
def validate_agent(model_uri: str) -> bool:
    """Run pre-deployment validation; return True if agent is ready."""
    try:
        result = mlflow.models.predict(
            model_uri=model_uri,
            input_data={"input": [{"role": "user", "content": "smoke test"}]},
        )
        if result is None:
            return False
        return True
    except Exception as exc:
        logger.error("Pre-deploy validation failed: %s", exc)
        return False
```

---

## 6. Complete Logging Workflow

End-to-end example combining all patterns:

```python
import mlflow
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
)

RESOURCES = [
    DatabricksServingEndpoint(endpoint_name="my-llm"),
    DatabricksVectorSearchIndex(index_name="prod.rag.documents"),
]


def log_and_validate_agent(agent_path: str, experiment_path: str) -> str:
    """Log agent, validate, and return model_uri."""
    mlflow.set_experiment(experiment_path)

    with mlflow.start_run(run_name="agent-logging") as run:
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=agent_path,
            input_example={"input": [{"role": "user", "content": "Hello"}]},
            resources=RESOURCES,
            pip_requirements=[
                "mlflow[databricks]>=3.10.1",
                "databricks-sdk>=0.40.0",
            ],
        )

        result = mlflow.models.predict(
            model_uri=model_info.model_uri,
            input_data={"input": [{"role": "user", "content": "test"}]},
        )
        assert result is not None, "Validation failed"

        mlflow.set_tag("validation", "passed")
        return model_info.model_uri
```

---

## 7. Common Logging Errors and Fixes

### Error: `set_model()` not called

```
MlflowException: The specified model file does not define a model object.
```

**Fix:** Add `mlflow.models.set_model(agent_instance)` at module level in the
agent file.

### Error: Signature mismatch at serving time

```
MlflowException: Model input does not match the expected schema
```

**Fix:** Remove any explicit `signature=` parameter. Let `ResponsesAgent` or
`ChatAgent` auto-infer. Verify with `mlflow.models.predict()` before deploy.

### Error: Missing pip dependency at load time

```
ModuleNotFoundError: No module named 'langchain_community'
```

**Fix:** Add the missing package to `pip_requirements` in `log_model()`.

### Error: Resource permission denied at inference

```
PermissionDenied: PERMISSION_DENIED: User does not have USE on endpoint
```

**Fix:** Add the missing resource declaration (e.g., `DatabricksServingEndpoint`).
The deployment surface uses declarations to provision SP access.

### Error: `log_model` fails with artifact path conflict

```
MlflowException: Artifact path 'agent' already exists in run
```

**Fix:** Use a unique `artifact_path` per log call, or log within a fresh
`mlflow.start_run()`.

### Error: Model too large for UC registration

```
RESOURCE_LIMIT_EXCEEDED: Model artifacts exceed maximum allowed size
```

**Fix:** Externalize large artifacts (e.g., vector stores, data files) as
resources instead of bundling them in the model directory.

---

## 8. DO / DON'T Summary

```python
# DON'T: Log without resources — deployment fails silently
mlflow.pyfunc.log_model(
    python_model=agent,
    artifact_path="agent",
)
```

```python
# DO: Always declare resources and validate before deploy
mlflow.pyfunc.log_model(
    python_model=agent,
    artifact_path="agent",
    resources=[DatabricksServingEndpoint(endpoint_name="my-llm")],
    input_example={"input": [{"role": "user", "content": "Hello"}]},
)
result = mlflow.models.predict(model_uri=model_info.model_uri, input_data=...)
```

```python
# DON'T: Forget set_model in the agent file
# agent.py
agent = MyAgent()
# (missing mlflow.models.set_model)
```

```python
# DO: Call set_model at module level
# agent.py
import mlflow
agent = MyAgent()
mlflow.models.set_model(agent)
```

```python
# DON'T: Use messages key in input example
input_example = {"messages": [{"role": "user", "content": "Hi"}]}
```

```python
# DO: Use input key
input_example = {"input": [{"role": "user", "content": "Hi"}]}
```

---
name: responses-agent-patterns
description: >
  MLflow ResponsesAgent implementation patterns for Databricks GenAI agents including
  streaming responses, MLflow tracing, OBO authentication with context detection, and
  Automatic Auth Passthrough. ResponsesAgent is MANDATORY for AI Playground compatibility.
  Use when creating new Databricks agents, implementing streaming responses, configuring
  OBO authentication, troubleshooting AI Playground errors, or adding MLflow tracing.
  Triggers on "ResponsesAgent", "predict_stream", "OBO", "auth passthrough",
  "AI Playground", "streaming agent", "trace context".
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/agent-bricks/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# ResponsesAgent Patterns

MLflow ResponsesAgent is **MANDATORY** for all new Databricks GenAI agents. It provides automatic signature inference, AI Playground compatibility, built-in tracing, and streaming support.

## When to Use

- Creating a new Databricks GenAI agent
- Implementing streaming responses (predict_stream)
- Configuring OBO authentication for Model Serving
- Adding MLflow tracing to agent functions
- Troubleshooting AI Playground compatibility
- Setting up Automatic Auth Passthrough for resources

## Critical Rules

### 1. ResponsesAgent is MANDATORY (Not ChatAgent, Not PythonModel)

```python
# ✅ CORRECT: ResponsesAgent
from mlflow.pyfunc import ResponsesAgent

class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        ...

# ❌ WRONG: Legacy patterns
class MyAgent(mlflow.pyfunc.ChatAgent):  # ❌ Breaks AI Playground
class MyAgent(mlflow.pyfunc.PythonModel):  # ❌ No auto-signature
```

### 2. NO Manual Signature Parameter

```python
# ✅ CORRECT: Auto-inference
mlflow.pyfunc.log_model(
    python_model=agent,
    # NO signature parameter!
)

# ❌ WRONG: Manual signature breaks AI Playground
mlflow.pyfunc.log_model(
    python_model=agent,
    signature=my_signature,  # ❌ NEVER!
)
```

### 3. Use `input` Key (Not `messages`)

```python
# ✅ CORRECT
input_example = {"input": [{"role": "user", "content": "Hello"}]}

# ❌ WRONG
input_example = {"messages": [{"role": "user", "content": "Hello"}]}
```

### 4. Return ResponsesAgentResponse

```python
import uuid

return ResponsesAgentResponse(
    output=[self.create_text_output_item(
        text=response_text,
        id=str(uuid.uuid4())
    )],
    custom_outputs={"source": "agent", "thread_id": thread_id}
)
```

## Streaming Pattern

```python
from mlflow.types.responses import (
    ResponsesAgentStreamEvent,
    ResponsesAgentStreamEventDelta,
    ResponsesAgentMessageContentDelta,
)
from typing import Generator

def predict_stream(
    self, request: ResponsesAgentRequest
) -> Generator[ResponsesAgentStreamEvent, None, None]:
    item_id = str(uuid.uuid4())
    
    for chunk in self._process_streaming(query):
        yield ResponsesAgentStreamEvent(
            type="output_item.delta",
            delta=ResponsesAgentStreamEventDelta(
                type="message_delta",
                delta=ResponsesAgentMessageContentDelta(
                    type="text", text=chunk
                )
            ),
            item_id=item_id,
        )
    
    # MANDATORY: Final done event
    yield ResponsesAgentStreamEvent(
        type="output_item.done",
        item_id=item_id,
    )
```

**For complete streaming patterns, see:** `references/streaming-patterns.md`

## OBO Authentication (Critical)

OBO (On-Behalf-Of) allows agents in Model Serving to query data with the caller's permissions. **Must detect context to avoid errors in notebooks/evaluation.**

```python
import os

def _get_authenticated_client(self):
    from databricks.sdk import WorkspaceClient
    
    is_model_serving = (
        os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true"
        or os.environ.get("DATABRICKS_SERVING_ENDPOINT") is not None
        or os.environ.get("MLFLOW_DEPLOYMENT_FLAVOR_NAME") == "databricks"
    )
    
    if is_model_serving:
        from databricks_ai_bridge import ModelServingUserCredentials
        return WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
    else:
        return WorkspaceClient()  # Default auth
```

**For complete OBO patterns including Auth Passthrough, see:** `references/obo-authentication.md`

## MLflow Tracing Quick Reference

```python
@mlflow.trace(name="my_function", span_type="TOOL")
def my_function(query: str) -> str:
    ...
```

| Span Type | Use For |
|---|---|
| `AGENT` | Top-level agent predict() |
| `TOOL` | Tool invocations (Genie, search) |
| `LLM` | Direct LLM calls |
| `RETRIEVER` | Memory/document retrieval |
| `MEMORY` | Memory operations |
| `JUDGE` | Evaluation scorers |

**For trace context patterns (tags vs metadata), see:** `references/trace-context-patterns.md`

**For visualization hint patterns (AI/BI dashboard integration), see:** `references/visualization-hints.md`

## Validation Checklist

- [ ] Agent inherits from `mlflow.pyfunc.ResponsesAgent`
- [ ] `predict()` returns `ResponsesAgentResponse`
- [ ] `predict_stream()` yields `ResponsesAgentStreamEvent`
- [ ] Final `output_item.done` event sent
- [ ] Input uses `input` key (NOT `messages`)
- [ ] NO `signature` parameter in `log_model()`
- [ ] OBO context detection implemented
- [ ] All resources declared in SystemAuthPolicy
- [ ] `@mlflow.trace` on key functions
- [ ] Agent loads in AI Playground

## References

- [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent)
- [MLflow Tracing](https://mlflow.org/docs/latest/llms/tracing/index.html)
- [Model Serving OBO](https://docs.databricks.com/en/machine-learning/model-serving/create-manage-serving-endpoints.html)
- [Unity Catalog Traces](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage)

## Version History

| Date | Changes |
|---|---|
| Jan 27, 2026 | OBO context detection fix, Auth Passthrough discovery |
| Jan 7, 2026 | ResponsesAgent made mandatory, NO LLM fallback pattern |

# Model Signatures and AI Playground Compatibility

Complete reference for MLflow model signatures in the Databricks GenAI ecosystem:
why they matter, what breaks without them, and how ResponsesAgent auto-inference works.

---

## Why Signatures Matter

> "Azure Databricks uses MLflow Model Signatures to define agents' input and
> output schema. Product features like the AI Playground assume that your agent
> has one of a set of supported model signatures."

Without a compatible signature:

- **AI Playground** will not load the agent
- **Agent Evaluation** cannot invoke the agent
- **Mosaic AI features** (monitoring, Gateway) cannot route requests
- **Model Serving endpoints** reject payloads that don't match the schema

Signatures act as the contract between your agent code and every Databricks
product surface that consumes it.

---

## Signature Auto-Inference (ResponsesAgent)

When you log a `ResponsesAgent` via `mlflow.pyfunc.log_model()`, MLflow
automatically infers a signature compatible with Databricks product features.
This is the **only recommended path** for new agents.

### How it works

1. MLflow inspects the `ResponsesAgent` class methods (`predict`, `predict_stream`)
2. It generates a signature matching the OpenAI Responses API schema
3. The signature is stored alongside the model artifact in the MLflow run
4. Downstream tools (Playground, Evaluation, Serving) read this signature

### Input Schema (auto-inferred)

```json
{
  "input": [
    {"role": "user", "content": "What is the total cost?"}
  ]
}
```

> **CRITICAL:** The key is `input`, NOT `messages`. This is a common source of
> incompatibility when migrating from ChatAgent or hand-rolling payloads.

### Output Schema (auto-inferred)

```json
{
  "output": [
    {
      "type": "message",
      "id": "msg_001",
      "content": [{"type": "output_text", "text": "The total cost is..."}],
      "role": "assistant"
    }
  ]
}
```

The output follows the OpenAI Responses API structure. Each item in `output`
has a `type` field that downstream consumers use for routing and rendering.

---

## Decision Table: When to Use Each Agent Type

| Agent Type | Signature | AI Playground | Agent Eval | Model Serving | Recommendation |
|---|---|---|---|---|---|
| `ResponsesAgent` | Auto-inferred | Compatible | Compatible | Compatible | **Use for all new agents** |
| `ChatAgent` | Auto-inferred (legacy) | Compatible | Compatible | Compatible | Maintain only if already migrating |
| `PythonModel` | Must be manual | Often breaks | Often breaks | Manual config | Avoid for LLM agents |

### When PythonModel is acceptable

- Non-LLM models (classic ML, feature engineering)
- Custom inference logic that doesn't fit the chat/responses paradigm
- Batch scoring pipelines without interactive UI requirements

For anything involving AI Playground, Agent Evaluation, or interactive serving,
always prefer `ResponsesAgent`.

---

## What Breaks Compatibility

### Anti-pattern 1: Manual Signature Override

```python
# WRONG: Manual signature breaks auto-inference
from mlflow.models.signature import ModelSignature, Schema, ColSpec

sig = ModelSignature(
    inputs=Schema([ColSpec("string", "messages")]),
    outputs=Schema([ColSpec("string", "response")]),
)
mlflow.pyfunc.log_model(
    python_model=agent,
    signature=sig,  # ← BREAKS AI Playground
)
```

```python
# CORRECT: Let MLflow infer the signature
mlflow.pyfunc.log_model(
    python_model=agent,
    input_example={"input": [{"role": "user", "content": "Hello"}]},
    # No signature= parameter — MLflow infers it from ResponsesAgent
)
```

**Why:** When you pass `signature=`, MLflow skips its auto-inference logic
entirely. The manual schema almost never matches what Playground expects.

### Anti-pattern 2: Wrong Input Key

```python
# WRONG: Using "messages" instead of "input"
input_example = {"messages": [{"role": "user", "content": "Hello"}]}

# CORRECT: ResponsesAgent expects "input"
input_example = {"input": [{"role": "user", "content": "Hello"}]}
```

**Why:** The Responses API schema uses `input` as the top-level key. Using
`messages` (the ChatAgent convention) produces a signature that Playground
and Evaluation cannot parse.

### Anti-pattern 3: Legacy Dict Output

```python
# WRONG: Returning a plain dict
def predict(self, request):
    return {"response": "Hello"}

# CORRECT: Returning ResponsesAgentResponse
from mlflow.types.responses import ResponsesAgentResponse
from uuid import uuid4

def predict(self, request):
    return ResponsesAgentResponse(
        output=[self.create_text_output_item(text="Hello", id=str(uuid4()))]
    )
```

**Why:** Dict returns produce an untyped signature. The structured
`ResponsesAgentResponse` ensures the output schema matches what Playground
renders and what Evaluation scores.

### Anti-pattern 4: Mixing Chat and Responses Conventions

```python
# WRONG: ChatAgent-style return in a ResponsesAgent
class MyAgent(ResponsesAgent):
    def predict(self, request):
        return {
            "choices": [{
                "message": {"role": "assistant", "content": "Hello"}
            }]
        }

# CORRECT: Use ResponsesAgent conventions
class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text="Hello", id=str(uuid4()))]
        )
```

---

## Verifying Signature Compatibility

After logging a model, always verify the signature before deployment:

```python
import mlflow

model_info = mlflow.pyfunc.log_model(
    python_model=agent,
    artifact_path="agent",
    input_example={"input": [{"role": "user", "content": "test"}]},
)

# 1. Inspect the auto-inferred signature
loaded = mlflow.pyfunc.load_model(model_info.model_uri)
print("Signature:", loaded.metadata.signature)

# 2. Verify input schema has "input" key (not "messages")
sig = loaded.metadata.signature
assert "input" in str(sig.inputs), "Signature missing 'input' key"

# 3. Pre-deployment validation with a real prediction
result = mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data={"input": [{"role": "user", "content": "validation test"}]},
)
assert result is not None, "Pre-deployment validation failed"
print("Validation passed:", result)
```

### Signature Fields to Check

| Field | Expected Value | Common Error |
|---|---|---|
| `inputs` | Contains `input` key with array type | Contains `messages` instead |
| `outputs` | Contains `output` key with structured type | Flat string or dict |
| `params` | Optional; may include `temperature`, etc. | Should not be required |

---

## Migration from ChatAgent to ResponsesAgent

If you have an existing `ChatAgent`, wrap it in a `ResponsesAgent`:

```python
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse
from uuid import uuid4


class MigratedAgent(ResponsesAgent):
    """Wraps a legacy ChatAgent in the ResponsesAgent interface."""

    def __init__(self):
        self.legacy = MyChatAgent()

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Convert ResponsesAgent input → ChatAgent input
        messages = [item.model_dump() for item in request.input]
        legacy_result = self.legacy.predict(
            context=None,
            model_input={"messages": messages},
        )

        # Convert ChatAgent output → ResponsesAgent output
        text = legacy_result["choices"][0]["message"]["content"]
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=text, id=str(uuid4()))]
        )
```

### Migration Checklist

- [ ] `predict()` accepts `ResponsesAgentRequest`, returns `ResponsesAgentResponse`
- [ ] Input is read from `request.input` (not `request.messages`)
- [ ] Output uses `create_text_output_item()` (not dict)
- [ ] `log_model()` has no `signature=` parameter
- [ ] `input_example` uses `{"input": [...]}` format
- [ ] Verified in AI Playground after logging

---

## Signature Interaction with Model Serving

When a model with an auto-inferred signature is deployed to a serving endpoint:

| Serving Feature | Behavior | Notes |
|---|---|---|
| Input validation | Enforced against signature schema | Rejects payloads with wrong keys |
| Output format | Matches signature output schema | Clients can rely on structure |
| AI Gateway routing | Uses signature to detect agent type | Wrong signature → wrong routing |
| Rate limiting | Applied per-endpoint, independent of signature | No signature impact |
| A/B testing | Requires matching signatures across variants | Mismatched signatures → errors |

---

## References

- [Model Signatures for Databricks Features](https://docs.databricks.com/en/generative-ai/agent-framework/create-agent.html)
- [MLflow Model Signatures](https://mlflow.org/docs/latest/models.html#model-signature)
- [ResponsesAgent API](https://mlflow.org/docs/latest/genai/responses-agent/)
- [AI Playground compatibility](https://docs.databricks.com/en/large-language-models/ai-playground.html)
- Related: [`anti-patterns.md`](anti-patterns.md) — expanded DO/DON'T examples
- Related: [`../../../01-experiment-tracing-setup/SKILL.md`](../../01-experiment-tracing-setup/SKILL.md) — tracing after logging

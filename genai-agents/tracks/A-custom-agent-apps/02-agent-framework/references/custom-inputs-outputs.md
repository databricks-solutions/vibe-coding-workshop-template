# Custom Inputs and Outputs

ResponsesAgent natively supports `custom_inputs` and `custom_outputs` for
passing additional data that falls outside the standard chat message format.

## When to Use

| Field | Direction | Purpose |
|---|---|---|
| `custom_inputs` | Client → Agent | Extra context: `client_type`, `session_id`, `user_id`, feature flags |
| `custom_outputs` | Agent → Client | Metadata: `thread_id`, retrieval source links, visualization hints |

Neither field is included in the chat history for future turns — they are
sideband data only.

## Accessing custom_inputs in Your Agent

```python
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        custom = request.custom_inputs or {}

        user_id = custom.get("user_id", "anonymous")
        session_id = custom.get("session_id")
        client_type = custom.get("client_type", "web")

        # Use these values for routing, tracing, memory, etc.
        ...
```

## Returning custom_outputs

```python
return ResponsesAgentResponse(
    output=[self.create_text_output_item(text=answer, id=item_id)],
    custom_outputs={
        "thread_id": thread_id,
        "session_id": session_id,
        "sources": [{"uri": doc.uri, "title": doc.title} for doc in sources],
    },
)
```

Clients use `custom_outputs` for:
- **`thread_id`** — continuing multi-turn conversations
- **Source links** — displaying references in the UI
- **Visualization hints** — see `references/visualization-hints.md`

## AI Playground and Review App Integration

You can provide `custom_inputs` when testing agents in both the
[AI Playground](https://docs.databricks.com/aws/en/getting-started/gen-ai-llm-agent)
and the
[Review App](https://docs.databricks.com/aws/en/generative-ai/agent-evaluation/review-app):

1. Open AI Playground or the Review App.
2. Click the **gear icon** (⚙️).
3. Enable **custom_inputs**.
4. Provide a JSON object matching your agent's expected schema:

```json
{
  "user_id": "analyst@acme.com",
  "session_id": "abc-123",
  "client_type": "playground"
}
```

**Caveat:** The Agent Evaluation Review App does **not** support rendering
traces for agents that require additional input fields. If your agent fails
without `custom_inputs`, evaluation via the Review App will not work. Design
agents to treat `custom_inputs` as optional with sensible defaults.

## Sending custom_inputs Programmatically

```python
import requests

response = requests.post(
    f"{app_url}/invocations",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "input": [{"role": "user", "content": "What were Q3 sales?"}],
        "custom_inputs": {
            "user_id": "analyst@acme.com",
            "session_id": "session-456",
        },
    },
)

data = response.json()
thread_id = data.get("custom_outputs", {}).get("thread_id")
```

## Common Patterns

### Thread tracking across turns

```python
# Turn 1: no thread_id in custom_inputs → agent creates one
# Response custom_outputs: {"thread_id": "t-abc"}

# Turn 2: client sends thread_id back
# Request custom_inputs: {"thread_id": "t-abc"}
# Agent loads conversation history for that thread
```

### Feature flags

```python
custom = request.custom_inputs or {}
if custom.get("enable_web_search"):
    agent_tools.append(web_search_tool)
```

### Trace enrichment

```python
custom = request.custom_inputs or {}
mlflow.update_current_trace(
    metadata={
        "mlflow.trace.user": custom.get("user_id", "unknown"),
        "mlflow.trace.session": custom.get("session_id", ""),
    }
)
```

## DO / DON'T

```python
# ✅ DO: Treat custom_inputs as optional with defaults
custom = request.custom_inputs or {}
user_id = custom.get("user_id", "anonymous")

# ❌ DON'T: Require custom_inputs (breaks Playground and evaluation)
user_id = request.custom_inputs["user_id"]  # KeyError if not provided
```

## References

- [Author an AI agent — Custom inputs and outputs](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent#-custom-inputs-and-outputs)
- [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent/)
- [AI Playground](https://docs.databricks.com/aws/en/getting-started/gen-ai-llm-agent)

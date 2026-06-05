# Querying Deployed Agents

Complete reference for querying agents deployed on Databricks Apps. Covers
DatabricksOpenAI client setup, OAuth authentication, non-streaming and
streaming invocations, custom_inputs passthrough, REST API curl examples,
and error handling.

Grounded in:
- [Query an agent deployed on Databricks](https://docs.databricks.com/aws/en/generative-ai/agent-framework/query-agent)
- [Author an agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)

---

## 1. Authentication

### 1.1 OAuth Requirement

Databricks Apps agents **require OAuth tokens**. Personal Access Tokens (PATs)
are **not supported** for querying agents on Apps.

```bash
# Fetch an OAuth token. IDE/CLI: authenticate first per PRE-REQUISITES §11.
# Genie Code: pre-authenticated — run via runDatabricksCli (no login step).
databricks auth token
```

### 1.2 Token Lifecycle

OAuth tokens are short-lived (typically 1 hour). For long-running clients:

- Use the `WorkspaceClient` which handles token refresh automatically
- Use `DatabricksOpenAI(workspace_client=w)` which inherits refresh behavior
- Do NOT cache raw tokens for extended periods

### 1.3 Service Principal Tokens

For programmatic access (CI/CD, automation):

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(
    host="https://your-workspace.cloud.databricks.com",
    client_id="<sp-client-id>",
    client_secret="<sp-client-secret>",
)
```

---

## 2. DatabricksOpenAI Client (Recommended)

### 2.1 Setup

```python
from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI

w = WorkspaceClient()
client = DatabricksOpenAI(workspace_client=w)
```

`DatabricksOpenAI` handles:
- Automatic OAuth token refresh
- Correct base URL construction
- Proper header injection
- ResponsesAgent-compatible request formatting

### 2.2 Non-Streaming Invocation

```python
app_name = "my-agent-app"
input_msgs = [{"role": "user", "content": "What is MLflow?"}]

response = client.responses.create(
    model=f"apps/{app_name}",
    input=input_msgs,
)

print(response.output_text)
```

The `model` parameter must include the `apps/` prefix for Apps-hosted agents.

### 2.3 Streaming Invocation

```python
app_name = "my-agent-app"
input_msgs = [{"role": "user", "content": "Explain agent evaluation."}]

stream = client.responses.create(
    model=f"apps/{app_name}",
    input=input_msgs,
    stream=True,
)

for chunk in stream:
    print(chunk, end="", flush=True)
```

Streaming delivers response chunks as Server-Sent Events (SSE). The client
iterator yields each chunk as it arrives.

### 2.4 Collecting the Full Streamed Response

```python
full_text = ""
for chunk in stream:
    if hasattr(chunk, "delta"):
        full_text += chunk.delta
print(full_text)
```

---

## 3. Custom Inputs (Passthrough)

### 3.1 Passing Custom Inputs

Use `extra_body` to pass `custom_inputs` through to the agent:

```python
response = client.responses.create(
    model=f"apps/{app_name}",
    input=input_msgs,
    extra_body={
        "custom_inputs": {
            "session_id": "sess-abc123",
            "thread_id": "thread-xyz",
            "user_id": "user@example.com",
        },
    },
)
```

### 3.2 Common Custom Input Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `session_id` | Group related conversations | `"sess-abc123"` |
| `thread_id` | Track conversation threads | `"thread-xyz"` |
| `user_id` | Identify the calling user | `"user@example.com"` |
| `client_type` | Distinguish UI vs API callers | `"chat_ui"` or `"api"` |
| `metadata` | Arbitrary key-value pairs | `{"source": "playground"}` |

### 3.3 Reading Custom Inputs in the Agent

In your `ResponsesAgent.predict()` method:

```python
class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        session_id = request.custom_inputs.get("session_id")
        user_id = request.custom_inputs.get("user_id")
        # Use these for session management, logging, etc.
        ...
```

### 3.4 Custom Inputs with Streaming

```python
stream = client.responses.create(
    model=f"apps/{app_name}",
    input=input_msgs,
    stream=True,
    extra_body={
        "custom_inputs": {
            "session_id": "sess-abc123",
        },
    },
)

for chunk in stream:
    print(chunk, end="", flush=True)
```

---

## 4. Trace Retrieval

### 4.1 Getting Trace IDs from Responses

Include the `x-mlflow-return-trace-id` header:

```python
response = client.responses.create(
    model=f"apps/{app_name}",
    input=input_msgs,
    extra_headers={"x-mlflow-return-trace-id": "true"},
)

trace_id = response.metadata["trace_id"]
print(f"Trace: {trace_id}")
```

### 4.2 Retrieving Full Traces

```python
import mlflow

client_mlflow = mlflow.MlflowClient()
trace = client_mlflow.get_trace(trace_id)
print(trace.data.spans)
```

---

## 5. REST API (curl)

### 5.1 Non-Streaming

```bash
# Generate token
TOKEN=$(databricks auth token --host https://your-workspace.cloud.databricks.com)

# Non-streaming request
curl --request POST \
  --url "https://my-agent-app.databricksapps.com/responses" \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "input": [{"role": "user", "content": "Hello"}]
  }'
```

### 5.2 Streaming

```bash
curl --request POST \
  --url "https://my-agent-app.databricksapps.com/responses" \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### 5.3 With Custom Inputs

```bash
curl --request POST \
  --url "https://my-agent-app.databricksapps.com/responses" \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "custom_inputs": {
      "session_id": "sess-abc123",
      "user_id": "user@example.com"
    }
  }'
```

### 5.4 With Trace ID

```bash
curl --request POST \
  --url "https://my-agent-app.databricksapps.com/responses" \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --header "x-mlflow-return-trace-id: true" \
  --data '{
    "input": [{"role": "user", "content": "Hello"}]
  }'
```

### 5.5 Invocations Endpoint (Legacy)

Some templates expose `/invocations` instead of `/responses`:

```bash
curl --request POST \
  --url "https://my-agent-app.databricksapps.com/invocations" \
  --header "Authorization: Bearer $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

Check your AgentServer configuration for the correct endpoint path.

---

## 6. Python SDK (Lower-Level)

### 6.1 Using OpenAI Client Directly

If `DatabricksOpenAI` is not available in your SDK version:

```python
from databricks.sdk import WorkspaceClient
from openai import OpenAI

w = WorkspaceClient()

client = OpenAI(
    base_url=f"{w.config.host}/serving-endpoints",
    api_key=w.config.token,
)

response = client.responses.create(
    model="apps/my-agent-app",
    input=[{"role": "user", "content": "Hello"}],
)
```

**Caveat:** This approach does not handle token refresh automatically.
Prefer `DatabricksOpenAI` when available.

### 6.2 Using requests Directly

For maximum control:

```python
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

resp = requests.post(
    f"https://my-agent-app.databricksapps.com/responses",
    headers={
        "Authorization": f"Bearer {w.config.token}",
        "Content-Type": "application/json",
    },
    json={
        "input": [{"role": "user", "content": "Hello"}],
        "custom_inputs": {"session_id": "sess-abc123"},
    },
)
print(resp.json())
```

---

## 7. Error Handling

### 7.1 Common Error Codes

| HTTP Code | Meaning | Likely Cause |
|-----------|---------|--------------|
| 401 | Unauthorized | PAT used instead of OAuth; expired token |
| 403 | Forbidden | SP lacks resource permissions |
| 404 | Not Found | Wrong app name or endpoint path |
| 422 | Unprocessable Entity | Invalid request schema (e.g. `messages` instead of `input`) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Agent code exception |
| 502 | Bad Gateway | App not running or starting |
| 503 | Service Unavailable | App compute not ready |

### 7.2 Handling Auth Errors

```python
from openai import AuthenticationError, APIError

try:
    response = client.responses.create(
        model=f"apps/{app_name}",
        input=input_msgs,
    )
except AuthenticationError:
    # Token expired or invalid — refresh and retry
    w = WorkspaceClient()
    client = DatabricksOpenAI(workspace_client=w)
    response = client.responses.create(
        model=f"apps/{app_name}",
        input=input_msgs,
    )
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

### 7.3 Streaming Error Propagation

Errors during streaming are propagated in the last SSE event:

```json
{
  "delta": "...",
  "databricks_output": {
    "error": {
      "error_code": "BAD_REQUEST",
      "message": "TimeoutException: Tool XYZ failed to execute."
    }
  }
}
```

Handle this in the client by checking each chunk for error data:

```python
for chunk in stream:
    if hasattr(chunk, "databricks_output") and chunk.databricks_output:
        error = chunk.databricks_output.get("error")
        if error:
            raise RuntimeError(f"Agent error: {error['message']}")
    # Process normal chunk
    ...
```

### 7.4 Retry Strategy

```python
import time

MAX_RETRIES = 3
BACKOFF_BASE = 2

for attempt in range(MAX_RETRIES):
    try:
        response = client.responses.create(
            model=f"apps/{app_name}",
            input=input_msgs,
        )
        break
    except APIError as e:
        if e.status_code in (429, 502, 503) and attempt < MAX_RETRIES - 1:
            wait = BACKOFF_BASE ** attempt
            time.sleep(wait)
            continue
        raise
```

---

## References

- [Query an agent (Databricks docs)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/query-agent)
- [DatabricksOpenAI API docs](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_openai.html)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [`apps-deployment-patterns.md`](apps-deployment-patterns.md) — deployment workflow
- [`local-dev-loop.md`](local-dev-loop.md) — local testing before deployment

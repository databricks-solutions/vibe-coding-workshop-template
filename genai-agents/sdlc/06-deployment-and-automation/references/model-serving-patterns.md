# Model Serving Patterns

Complete reference for authoring agents that run on Databricks Model Serving.
Grounded in the official documentation and patterns observed in this repository.

---

## 1. Distributed Environment Constraints

Model Serving deploys your logged model across **multiple replicas** behind a
load balancer. Every design assumption must account for this.

### No replica affinity

A multi-turn conversation may hit replica A on turn 1 and replica B on turn 2.
There is no sticky-session guarantee.

```text
Turn 1 → Replica A  (creates local state)
Turn 2 → Replica B  (local state is absent)
Turn 3 → Replica A  (replica may have restarted)
```

### Cold starts and restarts

Replicas are created, scaled, and terminated by the infrastructure. Any state
held only in process memory (instance variables, module-level caches, temp
files) may vanish between requests.

### Concurrency within a replica

A single replica can serve multiple requests concurrently. If your model stores
any mutable state at the class or module level, those structures must be
**thread-safe**.

---

## 2. State Reconstruction Per Request

Because replicas are stateless, every `predict()` call must be self-contained.

### The pattern

```python
import mlflow
from mlflow.pyfunc import PythonModel


class StatelessAgent(PythonModel):

    def predict(self, context, model_input, params=None):
        # Reconstruct everything from the request payload
        messages = model_input.get("input", [])
        custom = model_input.get("custom_inputs", {})

        thread_id = custom.get("thread_id")
        session_id = custom.get("session_id")

        # If you need history, fetch it from an external store
        if thread_id:
            history = self._load_history(thread_id)
            messages = history + messages

        # Process the request
        response = self._call_llm(messages)
        return {"output": response}

    def _load_history(self, thread_id: str) -> list[dict]:
        """Fetch conversation history from an external store (e.g. Lakebase)."""
        # Implementation depends on your state backend
        ...

    def _call_llm(self, messages: list[dict]) -> str:
        ...
```

### What NOT to do

```python
class BrokenAgent(PythonModel):
    def __init__(self):
        self.conversation_history = []  # Lost across replicas/restarts

    def predict(self, context, model_input, params=None):
        self.conversation_history.append(model_input)  # Thread-unsafe
        return self._call_llm(self.conversation_history)
```

Problems:
- `conversation_history` lives only in one replica's memory
- Concurrent requests mutate the same list without locks
- A replica restart resets the list

---

## 3. Thread-Safe State Design

If you must hold any mutable structure (caches, counters, circuit breakers),
protect it.

### Using `threading.Lock`

```python
import threading
from mlflow.pyfunc import PythonModel


class SafeCounterAgent(PythonModel):
    def __init__(self):
        self._lock = threading.Lock()
        self._request_count = 0

    def predict(self, context, model_input, params=None):
        with self._lock:
            self._request_count += 1
            count = self._request_count
        return {"output": f"Request #{count}", "count": count}
```

### Using `functools.lru_cache` for read-only lookups

Read-only caches are safe because `lru_cache` is thread-safe for reads.
But cache **invalidation** or **writes** still need protection.

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_table_schema(table_name: str) -> dict:
    """Cache is safe because schema rarely changes within a replica's lifetime."""
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    return w.tables.get(table_name).as_dict()
```

### Prefer stateless over thread-safe stateful

| Approach | Complexity | Correctness risk |
|----------|-----------|-----------------|
| Fully stateless (reconstruct per request) | Low | Low |
| Thread-safe mutable state | Medium | Medium (lock contention, deadlocks) |
| Module-level mutable globals | High | High (race conditions, replica drift) |

---

## 4. Complete Stateless Agent Example

End-to-end agent suitable for Model Serving deployment:

```python
"""Stateless agent for Databricks Model Serving.

- All state reconstructed from the request payload.
- Config loaded via MLflow ModelConfig (YAML).
- No asyncio — synchronous only.
- Thread-safe: no mutable shared state.
"""

import mlflow
from mlflow.pyfunc import PythonModel


class GenieOptimizationAgent(PythonModel):
    """Agent that answers questions about a Genie Space using its config."""

    def load_context(self, context):
        """Called once when the model is loaded into a replica.

        Safe for read-only initialization (loading config, creating clients).
        """
        config = mlflow.models.ModelConfig(
            development_config="config.yml"
        )
        self.endpoint_name = config.get("model_serving_endpoint")
        self.warehouse_id = config.get("warehouse_id")
        self.default_catalog = config.get("catalog")
        self.default_schema = config.get("schema")

    def predict(self, context, model_input, params=None):
        """Process a single request. Must be synchronous."""
        messages = model_input.get("input", [])
        custom = model_input.get("custom_inputs", {})

        space_id = custom.get("space_id", "")
        thread_id = custom.get("thread_id")

        # Reconstruct conversation if needed
        if thread_id:
            prior = self._fetch_thread(thread_id)
            messages = prior + messages

        # Call the downstream LLM endpoint
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        response = w.serving_endpoints.query(
            name=self.endpoint_name,
            messages=messages,
        )

        return {
            "output": response.choices[0].message.content,
            "metadata": {"space_id": space_id},
        }

    def _fetch_thread(self, thread_id: str) -> list[dict]:
        """Load prior messages from an external store."""
        ...
        return []
```

### Logging this agent

```python
import mlflow

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        python_model=GenieOptimizationAgent(),
        artifact_path="agent",
        model_config="config.yml",
        input_example={
            "input": [{"role": "user", "content": "What are the top tables?"}],
            "custom_inputs": {"space_id": "abc123"},
        },
    )
```

---

## 5. Scaling Considerations

### Replica count

| Setting | Effect |
|---------|--------|
| `min_replicas: 0` | Scale to zero when idle (cold start on next request) |
| `min_replicas: 1` | Always-on; no cold start but continuous cost |
| `max_replicas: N` | Upper bound on horizontal scale |

### Concurrency per replica

Each replica handles multiple concurrent requests. The `concurrency` setting
controls how many in-flight requests a single replica accepts before new
requests queue or spill to another replica.

```yaml
# In endpoint configuration (API or bundle)
served_entities:
  - entity_name: "main.my_schema.genie-optimizer-agent"
    entity_version: "3"
    workload_size: "Small"
    scale_to_zero_enabled: true
    max_concurrency_per_replica: 4
```

> **Don't use legacy `served_models:`.** The Databricks Model Serving API
> moved to `served_entities:` for new endpoint configs; bundle validation
> rejects `served_models` with `unknown field: served_models`. The canonical
> shape mirrors [`assets/templates/databricks-yml-serving-template.yaml`](../assets/templates/databricks-yml-serving-template.yaml)
> (line 44). For AI-Gateway-style endpoints that proxy an external provider,
> use the `external_model.databricks-model-serving` payload instead — see
> [F4: AI Gateway](../../../foundation/04-ai-gateway/SKILL.md) for the
> create-endpoint shape.

### Workload sizing guidance

| Workload size | Typical use | Memory | CPU |
|--------------|-------------|--------|-----|
| Small | Lightweight agents, routing | Low | 1–2 cores |
| Medium | RAG with embedding lookups | Moderate | 2–4 cores |
| Large | Heavy compute, large context | High | 4+ cores |

### GPU vs CPU

Most Python-based agents that call external LLM endpoints (Foundation Model
API, external APIs) need CPU only. GPU workload types are for models that run
inference locally (e.g. serving a fine-tuned model directly).

---

## 6. Initialization Timing

### `load_context()` vs `__init__()` vs `predict()`

| Method | When it runs | Safe for |
|--------|-------------|----------|
| `__init__()` | Object creation (before serialization and after deserialization) | Lightweight defaults only |
| `load_context(context)` | Once per replica, after model artifacts are loaded | Read-only init: load config, create clients |
| `predict(context, input)` | Every request | Request-scoped work, state reconstruction |

### Anti-pattern: heavy init

```python
# DON'T — runs during logging AND again per replica; may fail in restricted envs
class BadAgent(PythonModel):
    def __init__(self):
        self.client = WorkspaceClient()  # May not have creds at log time
        self.data = self._load_huge_dataset()  # Blocks model logging
```

```python
# DO — defer to load_context
class GoodAgent(PythonModel):
    def load_context(self, context):
        self.client = WorkspaceClient()
        config = mlflow.models.ModelConfig(development_config="config.yml")
        self.endpoint = config.get("endpoint")
```

---

## 7. The Asyncio Ban

Model Serving runs your model inside an existing event loop managed by the
serving infrastructure. Starting a nested `asyncio` loop causes:

```
RuntimeError: This event loop is already running
```

### Rules

- Do **not** call `asyncio.run()`, `asyncio.get_event_loop().run_until_complete()`,
  or `loop.run_forever()` inside `predict()`.
- Do **not** use `nest_asyncio` as a workaround — it patches CPython internals
  and causes unpredictable behavior under concurrency.
- If a dependency requires async (e.g. an async HTTP client), use the
  **synchronous** variant or wrap with `concurrent.futures.ThreadPoolExecutor`.

```python
# DON'T
import asyncio

class AsyncBrokenAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        return asyncio.run(self._async_predict(model_input))  # RuntimeError


# DO — use synchronous calls
import requests

class SyncAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        resp = requests.post(self.endpoint_url, json=model_input)
        return resp.json()
```

---

## 8. Streaming Response Patterns

For streaming endpoints, errors may appear in the **final chunk** rather than
as an HTTP-level error.

### Error detection in streaming

```python
def consume_stream(response_iter):
    """Consume a streaming response and detect terminal errors."""
    last_chunk = None
    for chunk in response_iter:
        last_chunk = chunk
        yield chunk

    # After stream ends, check the final chunk for errors
    if last_chunk and hasattr(last_chunk, "databricks_output"):
        error = last_chunk.databricks_output.get("error")
        if error:
            raise RuntimeError(
                f"Streaming error: {error.get('error_code')}: "
                f"{error.get('message')}"
            )
```

### Client-side handling

Clients consuming SSE or streaming responses must:

1. Accumulate all chunks
2. Parse the **last event** for `error_code` and `message` fields
3. Treat the presence of these fields as a failure even if HTTP status was 200

---

## 9. Health Checks and Readiness

Model Serving provides built-in health checks. Your model does not need to
implement custom health endpoints, but you should ensure that `load_context()`
completes quickly and does not block on external resources that may be
unavailable at startup.

| Consideration | Guidance |
|--------------|----------|
| Slow `load_context()` | Replicas are marked unhealthy if init takes too long |
| External dependency in init | Use lazy initialization or retry with backoff |
| Missing credentials | `WorkspaceClient()` in `load_context()` should work on Serving (auto-auth) |

---

## Related Skills

- **Skill 02 — ResponsesAgent patterns:** Agent implementation and logging
- **Skill 09 — Evaluation:** Quality gates that determine if a model version
  is ready for serving
- **Skill 10 — UC Model Management:** How model versions are registered before
  deployment to serving endpoints

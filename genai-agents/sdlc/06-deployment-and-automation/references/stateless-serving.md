# Stateless Serving Patterns

Why local state breaks on Model Serving, how to reconstruct state per request,
and patterns for short-term and long-term state management.

---

## 1. Why Local Caching Breaks

Model Serving is a **distributed, auto-scaling** environment:

```text
Request 1 → Replica A  (writes to self.cache)
Request 2 → Replica B  (self.cache is empty — different process)
Request 3 → Replica A  (replica restarted — self.cache is empty)
```

### Failure modes

| Pattern | Failure | Symptom |
|---------|---------|---------|
| `self.history = []` | Lost across replicas | Agent forgets conversation |
| `self.cache = {}` | Stale/missing data | Inconsistent responses |
| Module-level dict | Race conditions | Corrupted state under concurrency |
| `threading.local()` | Lost across requests | State disappears between turns |
| Temp files | Not shared across replicas | `FileNotFoundError` on other replica |

### The rule

> Treat every `predict()` call as if it is running on a fresh machine with
> no prior knowledge of any other request.

---

## 2. State Reconstruction from ResponsesAgentRequest

The `ResponsesAgentRequest` (or `ChatAgentRequest`) payload carries everything
the agent needs to reconstruct context for the current turn.

### Message history in the payload

```python
class MyAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        messages = model_input.get("input", [])
        # messages contains the FULL conversation so far:
        # [
        #   {"role": "user", "content": "What tables are available?"},
        #   {"role": "assistant", "content": "The space has 3 tables..."},
        #   {"role": "user", "content": "Show me the revenue table schema"},
        # ]
        response = self._call_llm(messages)
        return {"output": response}
```

The client is responsible for accumulating messages and sending the full
history on each turn. The agent does not store any history — it receives
it fresh every time.

### Extracting context from messages

```python
def _extract_context(self, messages: list[dict]) -> dict:
    """Pull structured context from the conversation history."""
    context = {"mentioned_tables": set(), "active_filters": {}}
    for msg in messages:
        content = msg.get("content", "")
        # Extract table mentions, filter values, etc.
        ...
    return context
```

---

## 3. Short-Term State via `custom_inputs`

For metadata that doesn't belong in the message history (session IDs, space
references, feature flags), use the `custom_inputs` field.

### Client sends custom_inputs

```python
# Client-side (e.g. FastAPI backend calling the serving endpoint)
response = w.serving_endpoints.query(
    name="genie-optimizer-agent",
    input={
        "input": [{"role": "user", "content": "Optimize this space"}],
        "custom_inputs": {
            "thread_id": "thread-abc-123",
            "session_id": "sess-xyz-789",
            "space_id": "01ef...",
            "catalog": "main",
            "schema": "genie_optimization",
        },
    },
)
```

### Agent reads custom_inputs

```python
class MyAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        messages = model_input.get("input", [])
        custom = model_input.get("custom_inputs", {})

        thread_id = custom.get("thread_id")
        space_id = custom.get("space_id")
        catalog = custom.get("catalog", self.default_catalog)

        # Use thread_id to fetch prior state from external store
        # Use space_id to scope operations
        ...
```

### What belongs in `custom_inputs` vs messages

| Data | Where | Why |
|------|-------|-----|
| User questions and assistant replies | `input` (messages) | Part of the conversation |
| Session/thread identifiers | `custom_inputs` | Metadata, not conversation content |
| Space/catalog/schema references | `custom_inputs` | Operational context |
| Feature flags | `custom_inputs` | Per-request configuration |
| User identity | `custom_inputs` or headers | Auth context |

---

## 4. External State Stores

For state that must persist across requests and be shared across replicas,
use an external store.

### Lakebase (PostgreSQL) for conversation history

```python
import psycopg2


def load_thread_history(thread_id: str, conn_params: dict) -> list[dict]:
    """Load conversation history from Lakebase."""
    conn = psycopg2.connect(**conn_params)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content, created_at "
                "FROM conversation_messages "
                "WHERE thread_id = %s "
                "ORDER BY created_at ASC",
                (thread_id,),
            )
            return [
                {"role": row[0], "content": row[1]}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def save_turn(thread_id: str, role: str, content: str, conn_params: dict):
    """Persist a single message to Lakebase."""
    conn = psycopg2.connect(**conn_params)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversation_messages (thread_id, role, content) "
                "VALUES (%s, %s, %s)",
                (thread_id, role, content),
            )
        conn.commit()
    finally:
        conn.close()
```

### Delta tables for durable optimization state

The Genie Space Optimizer uses Delta tables (`genie_opt_runs`,
`genie_opt_iterations`, etc.) for optimization state that must survive
across job runs and be queryable by the UI. This is **not** in-memory
caching — it's persistent storage accessed via Spark SQL.

### Redis / Memcached for volatile caches

For high-frequency read-only lookups (table schemas, config snapshots),
an external cache is appropriate. But for Model Serving on Databricks,
most agents should prefer:

1. **ModelConfig** for static config (loaded once per replica)
2. **Lakebase** for durable state (conversations, sessions)
3. **Delta** for analytics-grade state (optimization results, evaluations)
4. **No cache** for everything else (reconstruct per request)

---

## 5. The Asyncio Ban

Model Serving runs your `predict()` inside an existing event loop.

### What fails

```python
import asyncio

class BrokenAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        # All of these FAIL:
        asyncio.run(self._async_call())                    # RuntimeError
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._async_call())        # RuntimeError
        asyncio.get_event_loop().run_forever()             # Blocks forever
```

```
RuntimeError: This event loop is already running
```

### What works

```python
# Synchronous HTTP calls
import requests

class SyncAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        resp = requests.post(self.url, json={"query": "..."})
        return resp.json()
```

```python
# Databricks SDK (synchronous by default)
from databricks.sdk import WorkspaceClient

class SDKAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        w = WorkspaceClient()
        result = w.serving_endpoints.query(name=self.endpoint, ...)
        return result
```

```python
# ThreadPoolExecutor for blocking I/O parallelism
from concurrent.futures import ThreadPoolExecutor

class ParallelAgent(PythonModel):
    def load_context(self, context):
        self._executor = ThreadPoolExecutor(max_workers=4)

    def predict(self, context, model_input, params=None):
        futures = [
            self._executor.submit(self._fetch, table)
            for table in tables
        ]
        results = [f.result(timeout=30) for f in futures]
        return {"output": self._synthesize(results)}
```

### If a dependency requires async

Wrap it in a synchronous adapter using `concurrent.futures`:

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio


def run_async_in_thread(coro):
    """Run an async coroutine synchronously in a new thread."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result(timeout=60)


class AsyncWrappedAgent(PythonModel):
    def predict(self, context, model_input, params=None):
        result = run_async_in_thread(self._async_operation(model_input))
        return result
```

This works because `asyncio.run()` creates a **new** event loop in the
worker thread, avoiding the conflict with the serving infrastructure's
existing loop.

---

## 6. Pattern Summary

| Concern | Pattern | Example |
|---------|---------|---------|
| Conversation history | Send full history in `input` | Client accumulates messages |
| Session metadata | `custom_inputs` field | `thread_id`, `space_id` |
| Cross-replica persistence | External store (Lakebase, Delta) | Postgres for chat, Delta for analytics |
| Static config | `ModelConfig` YAML | Endpoints, catalogs, schemas |
| Async operations | Synchronous code or `ThreadPoolExecutor` | Never `asyncio.run()` in predict |
| Read-only lookups | `load_context()` or `lru_cache` | Table schemas, static metadata |

---

## Related Skills

- **Skill 00 — MLflow GenAI Foundation:** Environment detection, client reuse
- **Skill 02 — ResponsesAgent Patterns:** Request/response contract
- **Skill 11 (parent) — Model Serving:** Full deployment constraints and scaling

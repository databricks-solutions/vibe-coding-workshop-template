# Anti-Patterns: MLflow GenAI Foundation

Comprehensive DO/DON'T reference for MLflow 3.x GenAI agent development on
Databricks. Each entry shows the broken pattern, explains why, and provides
the correct alternative.

---

## 1. Manual Signature on ResponsesAgent

```python
# DON'T — overrides auto-inference, breaks AI Playground
sig = ModelSignature(inputs=Schema([ColSpec("string", "messages")]), ...)
mlflow.pyfunc.log_model(python_model=agent, signature=sig)
```

```python
# DO — let MLflow infer from ResponsesAgent type annotations
mlflow.pyfunc.log_model(
    python_model=agent,
    input_example={"input": [{"role": "user", "content": "Hello"}]},
)
```

Passing `signature=` skips auto-inference entirely. The hand-written schema
won't match what Playground, Evaluation, and Serving expect.

## 2. Wrong Input Key (`messages` vs `input`)

```python
# DON'T — ChatAgent key on a ResponsesAgent
input_example = {"messages": [{"role": "user", "content": "Hello"}]}
```

```python
# DO — Responses API uses "input"
input_example = {"input": [{"role": "user", "content": "Hello"}]}
```

Playground sends `input`; a `messages` schema causes 400 errors at inference.

## 3. PythonModel for LLM Agents

```python
# DON'T — no auto-inferred signature, no Playground integration
class MyAgent(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        return {"response": call_llm(model_input["messages"][0]["content"])}
```

```python
# DO — structured output, auto-inferred signature, tracing integration
class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        text = call_llm(request.input[-1].content)
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=text, id=str(uuid4()))]
        )
```

`PythonModel` requires manual signature and trace setup. `ResponsesAgent`
handles both automatically.

## 4. Late Autolog Placement

```python
# DON'T — calls before autolog() are invisible
def run_evaluation(space_id: str):
    setup_client()                  # ← not traced
    mlflow.openai.autolog()         # too late
    result = call_llm("Analyze")
    return result
```

```python
# DO — module-level captures everything
import mlflow
mlflow.openai.autolog()

def run_evaluation(space_id: str):
    setup_client()                  # ← traced
    return call_llm("Analyze")     # ← traced
```

Module-level autolog patches client libraries at import, covering all calls.

## 5. Python `str.format()` for Templates

```python
# DON'T — inconsistent with project convention, breaks partial formatting
name = "{catalog}.{schema}.genie_opt_{judge}".format(catalog="main", ...)
```

```python
# DO — project standard with safe partial substitution
from genie_space_optimizer.common.config import format_mlflow_template
name = format_mlflow_template(
    "{{ catalog }}.{{ schema }}.genie_opt_{{ judge }}",
    catalog="main", schema="genie_optimization", judge="syntax_validity",
)
```

`format_mlflow_template` uses `{{ }}` syntax, leaves missing keys as-is.

## 6. New Client per Iteration

```python
# DON'T — new TLS handshake per benchmark, rate limit risk
for b in benchmarks:
    w = WorkspaceClient()
    w.serving_endpoints.query(...)
```

```python
# DO — one client, reused connection pool
w = WorkspaceClient()
for b in benchmarks:
    w.serving_endpoints.query(...)
```

A single `WorkspaceClient` maintains an internal pool. Creating one per
iteration adds minutes of overhead at 100+ benchmarks.

## 7. Naive Environment Detection

```python
# DON'T — conflates 4 distinct environments into one flag
if "DATABRICKS" in str(os.environ):
    mode = "databricks"
```

```python
# DO — check from most-specific to least-specific
def detect_environment() -> str:
    if os.environ.get("IS_IN_DB_MODEL_SERVING_ENV"):
        return "model_serving"
    if os.environ.get("DATABRICKS_APP_NAME"):
        return "databricks_apps"
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        return "notebook"
    return "local"
```

Each environment has different auth, Spark, and tracing. A blanket check
causes `AttributeError` when code assumes Spark in Model Serving. See
[`environment-detection.md`](environment-detection.md) for the full impl.

## 8. Unpinned Dependencies

```yaml
# DON'T — may resolve MLflow 2.x with incompatible APIs
dependencies:
  - mlflow
  - databricks-sdk
```

```yaml
# DO — lower bounds ensure GenAI features exist
dependencies:
  - mlflow[databricks]>=3.10.1
  - databricks-sdk>=0.40.0
  - openai>=1.17
```

MLflow 2.x → 3.x has breaking changes in tracing, autolog, and
`ResponsesAgent`. The `[databricks]` extra includes workspace integration.

## 9. MLflow 2.x Patterns on 3.x

```python
# DON'T — deprecated idioms: manual URI, PythonModel, log_param
mlflow.set_tracking_uri("databricks")
with mlflow.start_run():
    mlflow.log_param("model", "gpt-4")
    mlflow.pyfunc.log_model(python_model=MyPythonModel(), signature=sig)
```

```python
# DO — 3.x patterns: autolog, ResponsesAgent, no manual URI
import mlflow
mlflow.openai.autolog()
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        python_model=MyResponsesAgent(),
        input_example={"input": [{"role": "user", "content": "test"}]},
    )
```

On Databricks, tracking URI is auto-detected. Autolog captures metrics
and traces. ResponsesAgent handles signatures.

## 10. Hardcoded UC Names

```python
# DON'T — breaks across workspaces, catalogs, and environments
table = "main.genie_optimization.genie_opt_syntax_validity"
exp = "/Shared/genie-space-optimizer/space_abc/billing"
```

```python
# DO — parameterized templates
from genie_space_optimizer.common.config import format_mlflow_template, EXPERIMENT_PATH_TEMPLATE
table = format_mlflow_template("{{ catalog }}.{{ schema }}.genie_opt_{{ judge }}", ...)
exp = format_mlflow_template(EXPERIMENT_PATH_TEMPLATE, space_id="abc", domain="billing")
```

Templates parameterize environment-specific values and support incremental
resolution as context becomes available.

## 11. No Pre-Deploy Validation

```python
# DON'T — register without validation; signature errors surface in production
model_info = mlflow.pyfunc.log_model(python_model=agent, artifact_path="agent")
mlflow.register_model(model_info.model_uri, "my_agent")
```

```python
# DO — validate locally before registering
model_info = mlflow.pyfunc.log_model(
    python_model=agent, artifact_path="agent",
    input_example={"input": [{"role": "user", "content": "test"}]},
)
result = mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data={"input": [{"role": "user", "content": "validate"}]},
)
assert result is not None, "Do not deploy"
mlflow.register_model(model_info.model_uri, "my_agent")
```

Local prediction catches signature mismatches and import errors before
the model reaches a serving endpoint.

## 12. Sync/Async Mixing

```python
# DON'T — calling async predict from sync generator deadlocks
class MyAgent(ResponsesAgent):
    async def predict(self, request): ...
    def predict_stream(self, request):
        result = self.predict(request)  # returns coroutine, not result
        yield result
```

```python
# DO — consistent execution model
class MyAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=self._call(request), id=str(uuid4()))]
        )
    def predict_stream(self, request: ResponsesAgentRequest):
        for chunk in self._stream(request):
            yield ResponsesAgentStreamEvent(data=chunk)
```

Both methods use sync execution. No async/sync boundary crossing.

---

## Quick Reference

| # | Anti-Pattern | Risk | Fix |
|---|---|---|---|
| 1 | Manual signature on ResponsesAgent | 🔴 Critical | Omit `signature=` |
| 2 | Wrong input key (`messages`) | 🔴 Critical | Use `input` key |
| 3 | PythonModel for LLM agents | 🟡 High | Use `ResponsesAgent` |
| 4 | Late autolog placement | 🟡 High | Module-level autolog |
| 5 | Single-brace templates | 🟡 Medium | `format_mlflow_template` |
| 6 | Client per iteration | 🟡 Medium | Shared client instance |
| 7 | Naive environment detection | 🟡 Medium | Check specific env vars |
| 8 | Unpinned dependencies | 🔴 Critical | Pin `>=` lower bounds |
| 9 | MLflow 2.x on 3.x | 🔴 Critical | Use 3.x patterns |
| 10 | Hardcoded UC names | 🟡 Medium | Template formatting |
| 11 | No pre-deploy validation | 🟡 High | `mlflow.models.predict` |
| 12 | Sync/async mixing | 🟡 Medium | Consistent execution model |

---

## References

- [`model-signatures.md`](model-signatures.md) — signature compatibility deep dive
- [`environment-detection.md`](environment-detection.md) — full detection implementation
- [MLflow 3.x migration guide](https://mlflow.org/docs/latest/getting-started/intro-quickstart/index.html)
- [ResponsesAgent API](https://mlflow.org/docs/latest/genai/responses-agent/)

# Autolog integrations — full reference

> **Companion to** [`../SKILL.md`](../SKILL.md) (Foundation Step 2).
>
> **Source:** [Automatic tracing — supported libraries](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic).

MLflow ships **`mlflow.<library>.autolog()`** integrations for 20+ GenAI
libraries. One line turns every model call, tool invocation, and agent
step into a span with token counts, latency, and inputs/outputs — no
manual `@mlflow.trace` required.

This reference enumerates every supported integration with the install
requirement, the autolog call, and a one-line "use when" so you can pick
the right one for your stack.

---

## How autolog works

```python
import mlflow

# Read the canonical path from state — pinned to
# /Users/<user_email>/mlflow/<APP_NAME>-agent by vibecoding-state.migrate_canonical.
mlflow.set_experiment(state["Resources"]["mlflow_experiment_path"])

mlflow.openai.autolog()   # any supported library

# from here on every OpenAI / library call is traced automatically
```

Call autolog **once, at module load**, *after* `mlflow.set_experiment(...)`
and *before* the first library call. Autolog is global — once enabled in
a process, every call to the instrumented library produces spans, no
matter where in the code it happens.

---

## LLM SDKs

| Library | Install | Autolog call | Use when |
|---|---|---|---|
| **OpenAI** (incl. Databricks Foundation Models, Azure OpenAI) | `pip install openai` | `mlflow.openai.autolog()` | Any OpenAI-compatible client (Foundation Models, Azure OpenAI, OpenRouter) — most common. |
| **Anthropic** | `pip install anthropic` | `mlflow.anthropic.autolog()` | Direct Claude SDK calls. |
| **Mistral AI** | `pip install mistralai` | `mlflow.mistral.autolog()` | Direct Mistral SDK calls. |
| **Google Gemini / GenAI** | `pip install google-genai` | `mlflow.gemini.autolog()` | Direct Gemini SDK calls. |
| **LiteLLM** | `pip install litellm` | `mlflow.litellm.autolog()` | Multi-provider router (OpenAI / Anthropic / Bedrock / Azure / …) abstracted behind one client. |
| **Bedrock (boto3)** | `pip install boto3` | `mlflow.bedrock.autolog()` | AWS Bedrock model invocations via the AWS SDK. |
| **DeepSeek** | `pip install openai` (DeepSeek uses OpenAI-compatible API) | `mlflow.openai.autolog()` | Use the OpenAI integration. |
| **Ollama** | `pip install ollama` (or use OpenAI-compatible mode) | `mlflow.openai.autolog()` (OpenAI-compatible) | Local Ollama via the OpenAI-compatible endpoint. |

---

## Orchestrators / agent frameworks

| Library | Install | Autolog call | Use when |
|---|---|---|---|
| **LangChain** | `pip install langchain` | `mlflow.langchain.autolog()` | Chains, retrievers, embeddings, tools authored with LangChain. |
| **LangGraph** | `pip install langgraph` | `mlflow.langchain.autolog()` (covers LangGraph) | Stateful graph-of-nodes workflows. |
| **LlamaIndex** | `pip install llama-index` | `mlflow.llama_index.autolog()` | Index-and-retrieve workflows over your own corpus. |
| **DSPy** | `pip install dspy-ai` | `mlflow.dspy.autolog()` | Declarative prompt programs / DSPy modules and signatures. |
| **OpenAI Agents SDK** | `pip install openai-agents` | `mlflow.openai.autolog()` (handlers cover Agents SDK) | Agent-OpenAI templates and the `agent-openai-agents-sdk` Apps template. |
| **Google ADK (Agent Development Kit)** | `pip install google-adk` | `mlflow.google_adk.autolog()` | Multi-agent orchestration with Google's ADK. |
| **CrewAI** | `pip install crewai` | `mlflow.crewai.autolog()` | Multi-agent role/task workflows. |
| **AutoGen** | `pip install autogen-agentchat` | `mlflow.autogen.autolog()` | Microsoft AutoGen multi-agent chats. |
| **smolagents** | `pip install smolagents` | `mlflow.smolagents.autolog()` | Lightweight code-agent loops (HuggingFace). |
| **Pydantic AI** | `pip install pydantic-ai` | `mlflow.pydantic_ai.autolog()` | Pydantic-typed agent definitions. |
| **Semantic Kernel** | `pip install semantic-kernel` | `mlflow.semantic_kernel.autolog()` | Microsoft Semantic Kernel plans/skills. |
| **Swarm** (OpenAI) | `pip install git+https://github.com/openai/swarm.git` | `mlflow.swarm.autolog()` | OpenAI Swarm multi-agent handoffs. |
| **Instructor** | `pip install instructor` | `mlflow.instructor.autolog()` | Pydantic-typed structured-output wrapping over LLM SDKs. |
| **AG2** (formerly AutoGen 0.2) | `pip install ag2` | `mlflow.ag2.autolog()` | AG2 multi-agent conversations. |

---

## Embedding / retriever / other

| Library | Install | Autolog call | Use when |
|---|---|---|---|
| **Sentence-Transformers** | `pip install sentence-transformers` | covered via LangChain / LlamaIndex autolog | Embedding within a LangChain or LlamaIndex pipeline. |
| **txtai** | `pip install txtai` | `mlflow.txtai.autolog()` | Embedding pipelines / semantic indexes. |
| **Groq** | `pip install groq` | `mlflow.groq.autolog()` | Direct Groq SDK calls. |

> The exact list of supported integrations evolves with each `mlflow`
> release. Always cross-check the live
> [Databricks docs page](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic)
> against your installed `mlflow` version.

---

## Combine multiple frameworks

Real agents often mix two or three of the above (e.g. LangGraph **plus**
direct OpenAI calls **plus** a few hand-rolled tools). Enable autolog for
**each framework** and use a top-level `@mlflow.trace` to roll everything
into a single trace:

```python
import mlflow
from langgraph.graph import StateGraph
from openai import OpenAI

mlflow.set_experiment(state["Resources"]["mlflow_experiment_path"])
# /Users/<user_email>/mlflow/<APP_NAME>-agent

# Enable every framework you use
mlflow.langchain.autolog()   # LangChain + LangGraph
mlflow.openai.autolog()      # direct OpenAI calls

client = OpenAI()


@mlflow.trace(name="run_agent", span_type="AGENT")
def run_agent(question: str) -> str:
    # LangGraph node — auto-traced as a child span
    state = build_graph().invoke({"question": question})

    # Direct OpenAI call — auto-traced as a sibling child span
    refinement = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": state["draft"]}],
    )

    return refinement.choices[0].message.content
```

The single root span `run_agent` collects every nested LangChain /
LangGraph / OpenAI span into one tree in the MLflow trace UI.

Source: [Auto-trace multiple frameworks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic#auto-trace-multiple-frameworks).

---

## Combining autolog with manual `@mlflow.trace`

Autolog spans nest naturally inside `@mlflow.trace` parents. Use this
pattern when you want one logical "agent step" to be searchable as a
unit but still want every LLM/tool call to be auto-instrumented.

```python
import mlflow
from openai import OpenAI

mlflow.openai.autolog()
client = OpenAI()


@mlflow.trace(name="classify_intent", span_type="AGENT")
def classify_intent(query: str) -> dict:
    # auto-traced child span: openai.chat.completions
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}],
    )
    return parse_intent(resp.choices[0].message.content)
```

In the trace UI you see:

```
classify_intent  (AGENT, manual)
  └─ openai.chat.completions  (LLM, auto)
```

This is the recommended **default** pattern for most Python agents: one
manual `@mlflow.trace` per logical step + autolog for everything below.

---

## Serverless-compute caveat

> On **Databricks serverless compute** (notebooks, jobs), MLflow autolog
> is **not** automatically enabled. You must call `autolog()` explicitly
> from your notebook / job entrypoint **before** the first library call.

Source: [Automatic tracing — Databricks serverless note](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic).

The same is true for **Databricks Apps** running custom Python code
(`@mlflow.genai.agent_server.invoke`-style agents). Always include the
`autolog()` call at module top-level in your `app.py` / `agent.py`:

```python
# app.py — top of file, before any LLM call
import mlflow

mlflow.set_experiment(EXPERIMENT_PATH)
mlflow.openai.autolog()    # explicit — required on serverless / Apps
```

Compare with classic interactive clusters where autolog hooks tend to
fire from the cluster's MLflow integration.

---

## Disabling autolog

Sometimes you want to selectively disable autolog (e.g. inside an
evaluation harness that already manages its own spans):

```python
mlflow.openai.autolog(disable=True)
```

Or scope it via a context manager pattern in your test fixtures.

---

## Validation checklist

- [ ] `mlflow.<library>.autolog()` called **after** `mlflow.set_experiment(...)` and **before** the first library call.
- [ ] Every framework used by the agent has an explicit `autolog()` call (no implicit auto-enable on serverless / Apps).
- [ ] Top-level orchestration wrapped in a `@mlflow.trace(name="run_agent", span_type="AGENT")` to give each request a single root span.
- [ ] Combined-framework agents verified: open one trace in the MLflow UI, confirm spans from each framework appear as children.
- [ ] Production / serverless deployments include the `autolog()` call in the deployed code (not only the notebook).

---

## Related

- [Foundation Step 2 (Python tracing)](../SKILL.md) — decision matrix, manual spans, UC OTEL storage.
- [Foundation Step 2b (TypeScript tracing)](../../02b-typescript-tracing/SKILL.md) — Node-native equivalent (`tracedOpenAI`, `mlflow.trace`, `withSpan`).
- [`references/tracing-patterns.md`](tracing-patterns.md) — manual decorator + span patterns.
- [`references/prod-tracing-deployment.md`](prod-tracing-deployment.md) — production env-var matrix for deployed agents.

---

## References

- [Databricks: Automatic tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic)
- [Databricks: Auto-trace multiple frameworks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/automatic#auto-trace-multiple-frameworks)
- [Databricks: Add traces to applications (decision matrix)](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/)

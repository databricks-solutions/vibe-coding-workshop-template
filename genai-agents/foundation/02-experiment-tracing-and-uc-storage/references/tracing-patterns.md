# Tracing Patterns — Complete Reference

> **Skill:** 01-experiment-tracing-setup
> **Grounded in:** `src/genie_space_optimizer/optimization/optimizer.py` —
> `_traced_llm_call()`, `start_span`, `SpanType`, `SpanEvent`

---

## 1. Span Types Reference

MLflow GenAI tracing defines several span types. Pick the type that matches the
work unit so the trace viewer renders meaningful icons and grouping.

| SpanType       | Import                                 | When to use                                        |
| -------------- | -------------------------------------- | -------------------------------------------------- |
| `AGENT`        | `from mlflow.entities import SpanType` | Top-level agent orchestration                      |
| `TOOL`         | same                                   | External API call, database query, file I/O        |
| `LLM`          | same                                   | Direct LLM inference call                          |
| `RETRIEVER`    | same                                   | Vector search, document retrieval, RAG fetch       |
| `JUDGE`        | same                                   | LLM-as-judge evaluation, scoring                   |
| `EMBEDDING`    | same                                   | Embedding model call                               |
| `CHAIN`        | same                                   | Multi-step orchestration (used by `_traced_llm_call`) |
| `CHAT_MODEL`   | same                                   | Auto-created by `mlflow.openai.autolog()`          |

---

## 2. Decorator-Based Tracing

The simplest way to add tracing. MLflow automatically records function inputs,
outputs, start/end time, and exceptions.

### Basic usage

```python
import mlflow


@mlflow.trace(name="classify_intent", span_type="AGENT")
def classify_intent(query: str) -> dict:
    """Classify the user's query into an intent category.

    The decorator wraps this function in a span. Inputs (query) and the
    return value are captured automatically.
    """
    intent = _run_classifier(query)
    return {"intent": intent, "confidence": 0.95}


@mlflow.trace(name="call_llm", span_type="LLM")
def call_llm(prompt: str, *, temperature: float = 0.7) -> str:
    """Call the LLM endpoint. All keyword args are recorded as span inputs."""
    response = client.chat.completions.create(
        model="databricks-claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content


@mlflow.trace(name="evaluate_response", span_type="JUDGE")
def evaluate_response(response: str, reference: str) -> float:
    """Score a response against a reference. Return value becomes span output."""
    return _compute_similarity(response, reference)


@mlflow.trace(name="search_documents", span_type="RETRIEVER")
def search_documents(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve relevant documents from the vector index."""
    return vector_index.similarity_search(query, k=top_k)


@mlflow.trace(name="embed_text", span_type="EMBEDDING")
def embed_text(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    return embedding_model.encode(texts)
```

### Decorator on async functions

```python
@mlflow.trace(name="async_llm_call", span_type="LLM")
async def async_llm_call(prompt: str) -> str:
    """Async functions are traced identically to sync functions."""
    response = await async_client.chat.completions.create(
        model="databricks-claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

---

## 3. Manual Span Creation

For fine-grained control — nested work units, partial inputs, retries, and
conditional branches — use `mlflow.start_span()` as a context manager.

### Pattern from `_traced_llm_call` in optimizer.py

The project's production tracing pattern (lines 158–237 of `optimizer.py`).
Condensed to highlight the structural decisions:

```python
import mlflow
from mlflow.entities import SpanEvent, SpanType

def _traced_llm_call(w, system_msg, prompt, *, span_name, max_retries=3, temperature=0.3):
    with mlflow.start_span(name=span_name, span_type=SpanType.CHAIN) as span:
        span.set_inputs({"model": LLM_ENDPOINT, "temperature": temperature, "prompt_chars": len(prompt)})

        last_err = None
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(model=LLM_ENDPOINT, messages=[...], temperature=temperature)
                text = response.choices[0].message.content.strip()
                _log_token_usage(span, response)
                span.set_outputs({"response_chars": len(text), "attempts": attempt + 1})
                return text, response
            except Exception as exc:
                last_err = exc
                span.add_event(SpanEvent(name=f"retry_{attempt+1}", attributes={"error": str(exc)[:500]}))

        span.set_outputs({"error": str(last_err)[:500], "attempts": max_retries})
        raise last_err
```

**Key patterns:** (1) `set_inputs()` before any work so partial traces show context,
(2) `_log_token_usage()` attaches cost data, (3) `SpanEvent` records each retry,
(4) `set_outputs()` on both success and failure paths.

---

## 4. Nested Span Example — Multi-Step Agent

A complete traced agent with nested LLM, tool, and judge spans:

```python
import mlflow
from mlflow.entities import SpanType


def run_optimization_agent(
    query: str,
    space_id: str,
    *,
    context: dict | None = None,
) -> dict:
    """Run a full optimization cycle with comprehensive tracing.

    Creates a parent AGENT span with nested children for each step:
    retrieval, LLM reasoning, tool execution, and judge evaluation.
    """
    with mlflow.start_span(
        name="optimization_agent", span_type=SpanType.AGENT
    ) as agent_span:
        agent_span.set_inputs({"query": query, "space_id": space_id})

        # Step 1: Retrieve relevant context
        with mlflow.start_span(
            name="retrieve_context", span_type=SpanType.RETRIEVER
        ) as retriever_span:
            retriever_span.set_inputs({"query": query, "top_k": 5})
            documents = search_knowledge_base(query, top_k=5)
            retriever_span.set_outputs({
                "doc_count": len(documents),
                "sources": [d["source"] for d in documents],
            })

        # Step 2: LLM reasoning
        with mlflow.start_span(
            name="strategist_reasoning", span_type=SpanType.LLM
        ) as llm_span:
            prompt = build_prompt(query, documents, context)
            llm_span.set_inputs({"prompt_chars": len(prompt)})
            strategy = call_llm(prompt)
            llm_span.set_outputs({"strategy_length": len(strategy)})

        # Step 3: Apply changes via tool
        with mlflow.start_span(
            name="apply_patches", span_type=SpanType.TOOL
        ) as tool_span:
            tool_span.set_inputs({"patch_count": len(strategy.get("patches", []))})
            result = apply_patches(space_id, strategy["patches"])
            tool_span.set_outputs({"applied": result["applied_count"]})

        # Step 4: Judge the outcome
        with mlflow.start_span(
            name="evaluate_outcome", span_type=SpanType.JUDGE
        ) as judge_span:
            judge_span.set_inputs({"response": strategy["summary"]})
            score = evaluate_quality(strategy["summary"], query)
            judge_span.set_outputs({"quality_score": score})

        agent_span.set_outputs({
            "strategy_id": strategy.get("id"),
            "patches_applied": result["applied_count"],
            "quality_score": score,
        })
        return {"strategy": strategy, "result": result, "score": score}
```

---

## 5. Error Handling in Traced Functions

Always record an outcome — even on failure — so the trace is useful for debugging:

```python
import mlflow
from mlflow.entities import SpanType

def traced_with_error_handling(query: str) -> dict:
    with mlflow.start_span(name="risky_op", span_type=SpanType.TOOL) as span:
        span.set_inputs({"query": query})
        try:
            result = perform_operation(query)
            span.set_outputs({"result": result, "status": "success"})
            return result
        except Exception as exc:
            span.set_outputs({"status": "error", "error": str(exc)[:500]})
            span.set_status("ERROR")
            raise
```

With `@mlflow.trace`, exceptions automatically mark the span as ERROR — no
extra handling needed for basic cases.

---

## 6. Trace Context Propagation Between Functions

When decorated functions call each other, MLflow automatically nests spans
under the active trace. No manual propagation needed:

```python
@mlflow.trace(name="outer_agent", span_type="AGENT")
def outer_agent(query: str) -> str:
    """Parent span — calls inner functions that create child spans."""
    context = retrieve_context(query)
    return generate_response(query, context)


@mlflow.trace(name="retrieve_context", span_type="RETRIEVER")
def retrieve_context(query: str) -> list[str]:
    return vector_search(query)


@mlflow.trace(name="generate_response", span_type="LLM")
def generate_response(query: str, context: list[str]) -> str:
    return call_llm(format_prompt(query, context))
```

For threaded or async pools, pass `request_id` from the parent span to child
spans so they remain linked in the same trace:

```python
import mlflow
from concurrent.futures import ThreadPoolExecutor


def parallel_evaluation(questions: list[str]) -> list[dict]:
    """Run evaluations in parallel while preserving trace hierarchy."""
    with mlflow.start_span(name="parallel_eval") as parent:
        parent.set_inputs({"question_count": len(questions)})
        request_id = mlflow.get_current_active_span().request_id

        def _eval_one(q: str) -> dict:
            with mlflow.start_span(name=f"eval_{q[:20]}", request_id=request_id) as child:
                child.set_inputs({"question": q})
                result = evaluate_single(q)
                child.set_outputs(result)
                return result

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_eval_one, questions))

        parent.set_outputs({"completed": len(results)})
        return results
```

---

## 7. Token Usage Logging

Pattern extracted from `_log_token_usage` in optimizer.py:

```python
from typing import Any


def _log_token_usage(span: Any, response: Any) -> None:
    """Attach token usage from an OpenAI response to an MLflow span.

    Records prompt_tokens, completion_tokens, and total_tokens as span
    attributes for cost analysis and optimization.
    """
    usage = getattr(response, "usage", None)
    if not usage:
        return

    attrs = {}
    if hasattr(usage, "prompt_tokens"):
        attrs["prompt_tokens"] = usage.prompt_tokens
    if hasattr(usage, "completion_tokens"):
        attrs["completion_tokens"] = usage.completion_tokens
    if hasattr(usage, "total_tokens"):
        attrs["total_tokens"] = usage.total_tokens

    if attrs:
        span.set_attributes(attrs)
```

---

## 8. Performance Tips for High-Throughput Tracing

### Batch span creation

Avoid creating thousands of trivially short spans. Group related work:

```python
# Prefer: single span for a batch
with mlflow.start_span(name="process_batch") as span:
    span.set_inputs({"batch_size": len(items)})
    results = [process(item) for item in items]
    span.set_outputs({"processed": len(results)})

# Avoid: one span per item in a 10,000-item loop
# for item in items:
#     with mlflow.start_span(name=f"process_{item.id}"):
#         process(item)
```

### Connection pool tuning

Set HTTP client defaults before heavy tracing traffic:

```python
import os

os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "5")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "120")
```

### Disable tracing in hot paths

For functions called thousands of times per second, use environment toggling:

```python
import os
import mlflow

_TRACING_ENABLED = os.getenv("ENABLE_FINE_TRACING", "false").lower() == "true"

def maybe_traced(x: int) -> int:
    if _TRACING_ENABLED:
        with mlflow.start_span(name="hot_path") as span:
            span.set_inputs({"x": x})
            result = expensive_computation(x)
            span.set_outputs({"result": result})
            return result
    return expensive_computation(x)
```

---

## 9. Combining Decorators and Manual Spans

Mix both styles — decorator for the outer function, manual spans for inner
steps that need fine-grained control:

```python
import mlflow
from mlflow.entities import SpanEvent, SpanType


@mlflow.trace(name="agent_pipeline", span_type="AGENT")
def agent_pipeline(query: str) -> dict:
    with mlflow.start_span(name="planning", span_type=SpanType.CHAIN) as plan_span:
        plan_span.set_inputs({"query": query})
        plan = create_plan(query)
        plan_span.set_outputs({"steps": len(plan["steps"])})

    results = []
    for i, step in enumerate(plan["steps"]):
        with mlflow.start_span(name=f"step_{i}", span_type=SpanType.TOOL) as step_span:
            step_span.set_inputs({"step": step["action"]})
            try:
                results.append(execute_step(step))
                step_span.set_outputs({"status": "ok"})
            except Exception as exc:
                step_span.add_event(SpanEvent(name="step_failed", attributes={"error": str(exc)[:200]}))
                step_span.set_outputs({"status": "error"})

    return {"plan": plan, "results": results}
```

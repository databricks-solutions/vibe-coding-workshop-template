# Wrapping Existing Agents with ResponsesAgent

Migrate LangChain/LangGraph chains, OpenAI Chat Completions code, or DSPy
programs to Databricks Model Serving **without rewriting core logic**. Each
wrapper converts `ResponsesAgentRequest` → framework format → execute →
`ResponsesAgentResponse` (and streaming events).

> **Prerequisite:** Your existing agent already works. The wrapper is a thin
> adapter; debug framework issues *before* wrapping.

---

## Message conversion helpers

Keep these as standalone functions so they are testable and reusable.

```python
"""Shared message conversion utilities for ResponsesAgent wrappers."""
from __future__ import annotations
from typing import Any


def responses_input_to_dicts(input_items: list[Any]) -> list[dict[str, str]]:
    """Convert ResponsesAgentRequest.input items to plain dicts."""
    return [item.model_dump() for item in input_items]


def last_user_content(messages: list[dict[str, str]]) -> str:
    """Extract the content string from the last user turn."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def dicts_to_langchain_messages(messages: list[dict[str, str]]) -> list:
    """Convert plain dicts to LangChain message objects."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    _MAP = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}
    return [_MAP.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]


def dicts_to_openai_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Strip extra keys — keep only role + content for OpenAI API."""
    return [{"role": m["role"], "content": m["content"]} for m in messages]
```

---

## 1. LangChain / LangGraph wrapper

Supports both `predict` and token-level `predict_stream` via `astream_events`.
For plain chains, replace `astream_events` with `chain.stream`.

```python
"""LangChain / LangGraph wrapper for ResponsesAgent."""
from __future__ import annotations
import asyncio
from typing import Any, Generator
from uuid import uuid4
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest, ResponsesAgentResponse, ResponsesAgentStreamEvent,
)
from .message_utils import dicts_to_langchain_messages, responses_input_to_dicts


class LangChainResponsesAgent(ResponsesAgent):
    """Wrap a LangChain Runnable or compiled LangGraph graph."""

    def __init__(self, chain_or_graph: Any | None = None) -> None:
        super().__init__()
        self._chain_or_graph = chain_or_graph

    def load_context(self, context: Any) -> None:
        if self._chain_or_graph is None:
            self._chain_or_graph = self._build_default_chain()

    def _build_default_chain(self) -> Any:
        raise NotImplementedError("Pass chain_or_graph or override _build_default_chain")

    @mlflow.trace(name="langchain_predict", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        messages = dicts_to_langchain_messages(responses_input_to_dicts(request.input))
        result = self._chain_or_graph.invoke({"messages": messages})
        text = self._extract_text(result)
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=text, id=str(uuid4()))],
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = dicts_to_langchain_messages(responses_input_to_dicts(request.input))
        item_id = str(uuid4())
        full_text = ""
        loop = asyncio.new_event_loop()
        try:
            async_gen = self._chain_or_graph.astream_events(
                {"messages": messages}, version="v2"
            )
            while True:
                try:
                    event = loop.run_until_complete(async_gen.__anext__())
                except StopAsyncIteration:
                    break
                if event["event"] == "on_chat_model_stream" and event["data"].get("chunk"):
                    token = event["data"]["chunk"].content
                    if token:
                        yield self.create_text_delta(delta=token, item_id=item_id)
                        full_text += token
        finally:
            loop.close()
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=full_text, id=item_id),
        )

    @staticmethod
    def _extract_text(result: Any) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict) and result.get("messages"):
            return result["messages"][-1].content
        return getattr(result, "content", str(result))

# agent = LangChainResponsesAgent(my_graph)
# mlflow.models.set_model(agent)
```

### Testing locally

```python
from mlflow.types.responses import ResponsesAgentRequest
req = ResponsesAgentRequest(input=[{"role": "user", "content": "Summarize Q3 results"}])
resp = agent.predict(req)
assert len(resp.output) >= 1
for ev in agent.predict_stream(req):
    if hasattr(ev, "delta"):
        print(ev.delta, end="", flush=True)
```

---

## 2. OpenAI Chat Completions wrapper

Migrates any `chat.completions.create` call (Databricks FMAPI, Azure OpenAI, openai.com).

```python
"""OpenAI Chat Completions wrapper for ResponsesAgent."""
from __future__ import annotations
from typing import Generator
from uuid import uuid4
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest, ResponsesAgentResponse, ResponsesAgentStreamEvent,
)
from openai import OpenAI
from .message_utils import dicts_to_openai_messages, responses_input_to_dicts


class OpenAICompletionsAgent(ResponsesAgent):
    """Wrap any OpenAI-compatible chat completions endpoint.

    Reads endpoint from ModelConfig — swap Databricks FMAPI / Azure / openai.com
    without code changes.
    """

    def __init__(self) -> None:
        super().__init__()
        config = mlflow.models.ModelConfig(development_config="config.yml")
        self._endpoint = config.get("model_serving_endpoint")
        self._max_tokens = config.get("max_tokens", 4096)
        self._temperature = config.get("temperature", 0.1)
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            import os
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            self._client = OpenAI(
                base_url=f"{w.config.host}/serving-endpoints",
                api_key=os.environ.get("DATABRICKS_TOKEN", w.config.token),
            )
        return self._client

    @mlflow.trace(name="openai_predict", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        messages = dicts_to_openai_messages(responses_input_to_dicts(request.input))
        completion = self.client.chat.completions.create(
            model=self._endpoint, messages=messages,
            max_tokens=self._max_tokens, temperature=self._temperature,
        )
        text = completion.choices[0].message.content or ""
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=text, id=str(uuid4()))],
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = dicts_to_openai_messages(responses_input_to_dicts(request.input))
        item_id = str(uuid4())
        full_text = ""
        stream = self.client.chat.completions.create(
            model=self._endpoint, messages=messages,
            max_tokens=self._max_tokens, temperature=self._temperature, stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield self.create_text_delta(delta=delta.content, item_id=item_id)
                full_text += delta.content
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=full_text, id=item_id),
        )

# agent = OpenAICompletionsAgent()
# mlflow.models.set_model(agent)
```

### Testing locally

```python
from mlflow.types.responses import ResponsesAgentRequest
agent = OpenAICompletionsAgent()
req = ResponsesAgentRequest(input=[{"role": "user", "content": "What is Unity Catalog?"}])
print(agent.predict(req).output[0].content[0].text)
for ev in agent.predict_stream(req):
    if hasattr(ev, "delta"):
        print(ev.delta, end="", flush=True)
```

---

## 3. DSPy wrapper

DSPy is synchronous — streaming yields the final answer as a single chunk.

```python
"""DSPy program wrapper for ResponsesAgent."""
from __future__ import annotations
import json
from typing import Any, Generator
from uuid import uuid4
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest, ResponsesAgentResponse, ResponsesAgentStreamEvent,
)
from .message_utils import last_user_content, responses_input_to_dicts


class DSPyResponsesAgent(ResponsesAgent):
    """Wrap a dspy.Module (ChainOfThought, ReAct, etc.).

    ``output_field`` controls which Prediction field becomes the response text.
    """

    def __init__(self, module: Any | None = None, output_field: str = "answer") -> None:
        super().__init__()
        self._module = module
        self._output_field = output_field

    def load_context(self, context: Any) -> None:
        if self._module is None:
            self._module = self._build_default_module()

    def _build_default_module(self) -> Any:
        raise NotImplementedError("Pass module or override _build_default_module")

    @mlflow.trace(name="dspy_predict", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        question = last_user_content(responses_input_to_dicts(request.input))
        prediction = self._module(question=question)
        text = self._prediction_to_text(prediction)
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=text, id=str(uuid4()))],
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """DSPy has no streaming API; emit result as one chunk."""
        question = last_user_content(responses_input_to_dicts(request.input))
        prediction = self._module(question=question)
        text = self._prediction_to_text(prediction)
        item_id = str(uuid4())
        yield self.create_text_delta(delta=text, item_id=item_id)
        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=text, id=item_id),
        )

    def _prediction_to_text(self, prediction: Any) -> str:
        value = getattr(prediction, self._output_field, None)
        if value is None:
            return json.dumps(prediction.toDict(), indent=2)
        return str(value)

# import dspy; dspy.configure(lm=dspy.LM("databricks/databricks-claude-sonnet-4-6"))
# agent = DSPyResponsesAgent(module=dspy.ChainOfThought("question -> answer"))
# mlflow.models.set_model(agent)
```

### Testing locally

```python
import dspy
from mlflow.types.responses import ResponsesAgentRequest
lm = dspy.LM("databricks/databricks-claude-sonnet-4-6")
dspy.configure(lm=lm)
agent = DSPyResponsesAgent(module=dspy.ChainOfThought("question -> answer"))
req = ResponsesAgentRequest(input=[{"role": "user", "content": "Why is the sky blue?"}])
print(agent.predict(req).output[0].content[0].text)
```

---

## Wrapper selection guide

| Existing framework | Wrapper class | Streaming | Notes |
|---|---|---|---|
| LangChain LCEL / RunnableSequence | `LangChainResponsesAgent` | Token-level via `astream_events` | Also works for LangGraph compiled graphs |
| OpenAI Chat Completions (any provider) | `OpenAICompletionsAgent` | Token-level via `stream=True` | Works with Databricks FMAPI, Azure, openai.com |
| DSPy Module | `DSPyResponsesAgent` | Single-chunk (no token streaming) | DSPy doesn't expose token callbacks |
| Custom Python function | Use the template in `assets/templates/agent-class-template.py` | Your choice | Simplest path for bespoke logic |

## Checklist before deploying a wrapper

- [ ] Wrapper `predict` returns `ResponsesAgentResponse` (not a dict or string)
- [ ] Wrapper `predict_stream` ends with a `response.output_item.done` event
- [ ] `mlflow.models.set_model(agent)` at module scope
- [ ] Message conversion tested: round-trip from `ResponsesAgentRequest` → framework → response
- [ ] `@mlflow.trace` decorates the top-level `predict` (or the inner framework call)
- [ ] OBO / serving detection handled if the wrapper calls UC or SQL (see `obo-authentication.md`)
- [ ] `ModelConfig` used for endpoint names, not hardcoded strings
- [ ] Local `predict` + `predict_stream` both succeed before `log_model`

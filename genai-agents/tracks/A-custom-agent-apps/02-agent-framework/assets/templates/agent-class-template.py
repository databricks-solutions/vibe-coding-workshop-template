"""
Agent Template: ResponsesAgent with streaming support.

Usage:
    1. Copy this file as your agent.py
    2. Implement your logic in _stream_response()
    3. Set mlflow.models.set_model(MyAgent())

Requires:
    - mlflow >= 3.1  (ResponsesAgent)
    - databricks-sdk  (for WorkspaceClient / FMAPI)

Quick test (notebook or local):
    >>> from mlflow.types.responses import ResponsesAgentRequest
    >>> agent = MyAgent()
    >>> req = ResponsesAgentRequest(input=[{"role": "user", "content": "Hi"}])
    >>> resp = agent.predict(req)
    >>> print(resp.output[0].content[0].text)
"""

from __future__ import annotations

import os
from typing import Any, Generator
from uuid import uuid4

import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

# ---------------------------------------------------------------------------
# Configuration — loaded from config.yml via ModelConfig
# Override at log time: log_model(..., model_config="prod-config.yml")
# ---------------------------------------------------------------------------
config = mlflow.models.ModelConfig(development_config="config.yml")
SERVING_ENDPOINT = config.get("model_serving_endpoint")
MAX_TOKENS = config.get("max_tokens", 4096)
TEMPERATURE = config.get("temperature", 0.1)


class MyAgent(ResponsesAgent):
    """Production-grade ResponsesAgent template with streaming."""

    # Optional: heavy one-time setup (model loading, index clients, etc.)
    # def load_context(self, context) -> None:
    #     self._client = ...

    # -- non-streaming (delegates to stream) --------------------------------

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        output_items = []
        for event in self.predict_stream(request):
            if event.type == "response.output_item.done":
                output_items.append(event.item)
        return ResponsesAgentResponse(output=output_items)

    # -- streaming ----------------------------------------------------------

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = [i.model_dump() for i in request.input]
        item_id = str(uuid4())
        full_text = ""

        for chunk in self._stream_response(messages):
            yield self.create_text_delta(delta=chunk, item_id=item_id)
            full_text += chunk

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(text=full_text, id=item_id),
        )

    # -- your LLM call goes here -------------------------------------------

    @mlflow.trace(name="llm_call", span_type="LLM")
    def _stream_response(
        self, messages: list[dict[str, Any]]
    ) -> Generator[str, None, None]:
        """Replace this with your actual LLM / chain / tool call.

        Example using Databricks FMAPI via OpenAI SDK:

            from openai import OpenAI
            client = OpenAI(
                base_url=f"{os.environ['DATABRICKS_HOST']}/serving-endpoints",
                api_key=os.environ["DATABRICKS_TOKEN"],
            )
            stream = client.chat.completions.create(
                model=SERVING_ENDPOINT,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        """
        raise NotImplementedError("Implement your streaming LLM call here")


# ---------------------------------------------------------------------------
# Register — MLflow resolves this when loading the model
# ---------------------------------------------------------------------------
agent = MyAgent()
mlflow.models.set_model(agent)

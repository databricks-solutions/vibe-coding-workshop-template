# Streaming Response Patterns

## Complete Streaming Implementation

```python
from typing import Generator
import uuid
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    ResponsesAgentStreamEventDelta,
    ResponsesAgentMessageContentDelta,
)

def predict_stream(
    self, request: ResponsesAgentRequest
) -> Generator[ResponsesAgentStreamEvent, None, None]:
    """
    Stream response chunks as they're generated.
    
    Event types:
    - output_item.delta: Partial text content
    - output_item.done: Marks completion of output item
    """
    input_messages = [msg.model_dump() for msg in request.input]
    query = input_messages[-1].get("content", "")
    item_id = str(uuid.uuid4())
    
    # Stream text chunks
    for chunk in self._process_streaming(query):
        yield ResponsesAgentStreamEvent(
            type="output_item.delta",
            delta=ResponsesAgentStreamEventDelta(
                type="message_delta",
                delta=ResponsesAgentMessageContentDelta(
                    type="text",
                    text=chunk
                )
            ),
            item_id=item_id,
        )
    
    # MANDATORY: Final done event
    yield ResponsesAgentStreamEvent(
        type="output_item.done",
        item_id=item_id,
    )
```

## Code Reuse: predict() Delegates to predict_stream()

```python
def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    """Non-streaming predict that collects stream output."""
    chunks = []
    for event in self.predict_stream(request):
        if event.type == "output_item.delta" and event.delta:
            chunks.append(event.delta.delta.text)
    
    full_text = "".join(chunks)
    return ResponsesAgentResponse(
        output=[self.create_text_output_item(
            text=full_text, id=str(uuid.uuid4())
        )]
    )
```

## Why the `done` Event Matters

The `output_item.done` event is not just a client-side signal — it triggers
critical Databricks platform behavior:

| System | What `done` Triggers |
|---|---|
| **MLflow Tracing** | Aggregates all streamed deltas into a single trace output |
| **AI Gateway** | Logs the complete response to inference tables |
| **AI Playground** | Displays the finalized message in the conversation UI |

Without `done`, traces show incomplete output, inference tables miss the
response, and Playground may render partial or empty messages.

## Streaming Error Propagation

Mosaic AI propagates errors encountered during streaming with the **last token**
under `databricks_output.error`. The calling client must handle this field.

```json
{
  "delta": "...",
  "databricks_output": {
    "trace": {},
    "error": {
      "error_code": "BAD_REQUEST",
      "message": "TimeoutException: Tool XYZ failed to execute."
    }
  }
}
```

Handle this on the client side:

```python
import json

async def consume_stream(response):
    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        data = json.loads(line[6:])

        db_output = data.get("databricks_output", {})
        if db_output.get("error"):
            error = db_output["error"]
            raise RuntimeError(
                f"[{error['error_code']}] {error['message']}"
            )

        if "delta" in data:
            yield data["delta"]
```

## Event Types Reference

| Event Type | Purpose | When to Yield |
|---|---|---|
| `output_item.delta` | Partial text content | Each text chunk |
| `output_item.done` | Completion marker (triggers tracing, logging, UI display) | After all deltas |

## Common Mistakes

```python
# ❌ WRONG: Missing done event
def predict_stream(self, request):
    for chunk in process():
        yield ResponsesAgentStreamEvent(type="output_item.delta", ...)
    # Missing done event! Client hangs.

# ✅ CORRECT: Always send done event
def predict_stream(self, request):
    for chunk in process():
        yield ResponsesAgentStreamEvent(type="output_item.delta", ...)
    yield ResponsesAgentStreamEvent(type="output_item.done", item_id=item_id)
```

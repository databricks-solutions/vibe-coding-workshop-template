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

## Event Types Reference

| Event Type | Purpose | When to Yield |
|---|---|---|
| `output_item.delta` | Partial text content | Each text chunk |
| `output_item.done` | Completion marker | After all deltas |

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

# Common ResponsesAgent Mistakes

## ResponsesAgent Interface Mistakes

### 1. Using ChatAgent Instead of ResponsesAgent

```python
# ❌ WRONG: ChatAgent is legacy
class MyAgent(mlflow.pyfunc.ChatAgent):
    def predict(self, context, model_input):
        ...

# ✅ CORRECT: ResponsesAgent is mandatory
class MyAgent(mlflow.pyfunc.ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        ...
```

### 2. Using `messages` Key Instead of `input`

```python
# ❌ WRONG: Legacy format
input_example = {"messages": [{"role": "user", "content": "Hello"}]}

# ✅ CORRECT: ResponsesAgent format
input_example = {"input": [{"role": "user", "content": "Hello"}]}
```

### 3. Manual Signature Parameter

```python
# ❌ WRONG: Overrides auto-inference
mlflow.pyfunc.log_model(python_model=agent, signature=my_sig)

# ✅ CORRECT: Auto-inference
mlflow.pyfunc.log_model(python_model=agent)
```

### 4. Missing set_model() Call

```python
# ❌ WRONG: MLflow can't find the model
class MyAgent(ResponsesAgent):
    ...
# File ends without set_model()

# ✅ CORRECT: Register model at module level
class MyAgent(ResponsesAgent):
    ...

mlflow.models.set_model(MyAgent())
```

### 5. Wrong Predict Signature

```python
# ❌ WRONG: Legacy signature
def predict(self, context, model_input, params=None):
    ...

# ✅ CORRECT: ResponsesAgent signature
def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    ...
```

### 6. Returning Wrong Type

```python
# ❌ WRONG: Dict return
def predict(self, request):
    return {"response": "Hello"}

# ✅ CORRECT: ResponsesAgentResponse
def predict(self, request):
    return ResponsesAgentResponse(
        output=[self.create_text_output_item(text="Hello", id=str(uuid.uuid4()))]
    )
```

---

## Trace Context Mistakes

### 7. Hardcoded Deployment Context

```python
# ❌ WRONG: Hardcoded environment
mlflow.update_current_trace(
    metadata={"mlflow.source.type": "PRODUCTION"}  # Hardcoded!
)

# ✅ CORRECT: From environment variables
mlflow.update_current_trace(
    metadata={
        "mlflow.source.type": os.getenv("APP_ENVIRONMENT", "DEV")  # Dynamic!
    }
)
```

### 8. Custom Fields for Standard Context

```python
# ❌ WRONG: Custom field names for standard concepts
mlflow.update_current_trace(
    metadata={
        "user": "user123",          # Wrong field name!
        "conversation": "session1"  # Wrong field name!
    }
)

# ✅ CORRECT: Standard field names (enables UI filtering)
mlflow.update_current_trace(
    metadata={
        "mlflow.trace.user": "user123",       # Standard!
        "mlflow.trace.session": "session1"    # Standard!
    }
)
```

### 9. Updating Metadata on Finished Traces

```python
# ❌ WRONG: Metadata is immutable after logging
trace_id = mlflow.get_last_active_trace_id()

mlflow.update_current_trace(
    metadata={"new_field": "value"}  # Won't work on finished trace!
)

# ✅ CORRECT: Use tags for post-logging updates (tags are mutable)
trace_id = mlflow.get_last_active_trace_id()

mlflow.set_trace_tag(
    trace_id=trace_id,
    key="review_status",
    value="approved"  # Works!
)
```

### 10. Unsafe Trace Update Without Checking

```python
# ❌ WRONG: Causes warnings during evaluation
def my_function():
    mlflow.update_current_trace(metadata={"key": "value"})  # May not have active trace!

# ✅ CORRECT: Check for active trace first
def my_function():
    try:
        current_span = mlflow.get_current_active_span()
        if current_span:
            mlflow.update_current_trace(metadata={"key": "value"})  # Safe!
    except Exception:
        pass  # No active trace, skip
```

### 11. Mixing Tags and Metadata Incorrectly

```python
# ❌ WRONG: Putting mutable data in metadata (can't update later)
mlflow.update_current_trace(
    metadata={
        "review_status": "pending",  # Can't change this after trace completes!
    }
)

# ✅ CORRECT: Mutable data goes in tags
mlflow.update_current_trace(
    tags={
        "review_status": "pending",  # Can update to "approved" later
    }
)
```

### 12. Forgetting to Return IDs in custom_outputs

```python
# ❌ WRONG: Client can't track conversations
return ResponsesAgentResponse(
    output=[self.create_text_output_item(text=response, id=str(uuid.uuid4()))]
)

# ✅ CORRECT: Return IDs for client-side tracking
return ResponsesAgentResponse(
    output=[self.create_text_output_item(text=response, id=str(uuid.uuid4()))],
    custom_outputs={
        "thread_id": thread_id,     # Client needs this for follow-up
        "session_id": session_id,   # Client needs this for multi-turn
        "domains_queried": domains, # Client needs this for context
    }
)
```

# Model Signatures: AI Playground Compatibility

## Why Signatures Matter

> "Azure Databricks uses **MLflow Model Signatures** to define agents' input and output schema. Product features like the **AI Playground assume that your agent has one of a set of supported model signatures**."
> — [Microsoft Docs](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent)

## AI Playground Compatibility

The AI Playground requires agents to have compatible model signatures. Without proper signatures:
- ❌ AI Playground won't load your agent
- ❌ Agent Evaluation won't work
- ❌ Mosaic AI features won't function

## Auto-Inference from ResponsesAgent

> "If you follow the **recommended approach to authoring agents**, MLflow will **automatically infer a signature** for your agent that is compatible with Azure Databricks product features, with **no additional work required** on your part."
> — [Microsoft Docs](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent)

### The Golden Rule

**Use `ResponsesAgent` and let MLflow auto-infer the signature. Never define signatures manually.**

## What Breaks Compatibility

| Issue | Impact | Example |
|---|---|---|
| Manual signature with wrong schema | ❌ AI Playground won't load | `signature=ModelSignature(...)` with wrong schema |
| `PythonModel` instead of `ResponsesAgent` | ❌ No signature inference | `class MyAgent(PythonModel)` |
| `messages` input instead of `input` | ❌ Request format mismatch | `input_example = {"messages": [...]}` |
| Legacy dict output instead of `ResponsesAgentResponse` | ❌ Response parsing fails | `return {"messages": [...]}` |

## Correct Pattern: ResponsesAgent

```python
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

class MyAgent(ResponsesAgent):
    """Agent implementing ResponsesAgent for AI Playground compatibility."""
    
    @mlflow.trace(name="my_agent", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Handle inference requests using ResponsesAgent interface."""
        # Extract query from input (ResponsesAgent uses 'input', not 'messages')
        input_messages = [msg.model_dump() for msg in request.input]
        query = input_messages[-1].get("content", "")
        
        # Process query
        response_text = self._process(query)
        
        # Return ResponsesAgentResponse using helper method
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(
                text=response_text,
                id=str(uuid.uuid4())
            )],
            custom_outputs={"source": "my_agent"}
        )
```

## Logging Without Manual Signature

```python
import mlflow

agent = MyAgent()

# CRITICAL: Set model before logging
mlflow.models.set_model(agent)

# Input example using ResponsesAgent format (input, NOT messages)
input_example = {
    "input": [{"role": "user", "content": "What is the status?"}]
}

with mlflow.start_run():
    # ================================================================
    # CRITICAL: DO NOT pass signature parameter!
    # ResponsesAgent automatically infers the correct signature.
    # Manual signatures WILL BREAK AI Playground compatibility.
    # ================================================================
    logged_model = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=agent,
        input_example=input_example,
        # signature=...  # ❌ NEVER include this!
        registered_model_name="my_agent",
        pip_requirements=[
            "mlflow>=3.0.0",
            "databricks-sdk>=0.28.0",
        ],
    )
```

## Input/Output Format

### Input Format (`request.input`)

```python
{
    "input": [
        {"role": "user", "content": "Why did costs spike yesterday?"}
    ],
    "custom_inputs": {  # Optional
        "user_id": "user123",
        "session_id": "session456"
    }
}
```

### Output Format (`ResponsesAgentResponse`)

```python
ResponsesAgentResponse(
    output=[
        {
            "type": "message",
            "id": "msg_123",
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": "The cost spike was due to..."}
            ]
        }
    ],
    custom_outputs={"domain": "cost", "source": "genie"}
)
```

## Helper Methods

```python
# Create text output item
self.create_text_output_item(text="Response text", id="msg_123")

# Create function call item (for tool calling)
self.create_function_call_item(
    id="fc_1",
    call_id="call_1",
    name="get_weather",
    arguments='{"city": "Boston"}'
)

# Create function call output item
self.create_function_call_output_item(
    call_id="call_1",
    output="72°F, Sunny"
)
```

## Verification

After logging your agent:

1. **Check AI Playground:**
   - Navigate to AI Playground in Databricks
   - Select your agent model
   - Verify it loads without errors

2. **Check Model Signature:**
   ```python
   from mlflow import MlflowClient
   
   client = MlflowClient()
   model = client.get_model_version("my_agent", "1")
   print(model.signature)  # Should show auto-inferred signature
   ```

3. **Test Inference:**
   ```python
   import mlflow
   
   model = mlflow.pyfunc.load_model("models:/my_agent/1")
   result = model.predict({
       "input": [{"role": "user", "content": "Test query"}]
   })
   print(result)  # Should be ResponsesAgentResponse object
   ```

## Common Mistakes

### ❌ Using PythonModel

```python
# ❌ WRONG: PythonModel doesn't auto-infer compatible signature
class MyAgent(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input):
        return {"messages": [...]}  # Wrong format!

# ✅ CORRECT: ResponsesAgent auto-infers signature
class MyAgent(mlflow.pyfunc.ResponsesAgent):
    def predict(self, request):
        return ResponsesAgentResponse(output=[...])
```

### ❌ Manual Signature Definition

```python
# ❌ WRONG: Manual signature breaks auto-inference
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import Schema, ColSpec

signature = ModelSignature(
    inputs=Schema([ColSpec("string", "messages")]),
    outputs=Schema([ColSpec("string", "messages")])
)

mlflow.pyfunc.log_model(
    python_model=agent,
    signature=signature,  # ❌ This breaks AI Playground!
    ...
)

# ✅ CORRECT: Let MLflow infer signature
mlflow.pyfunc.log_model(
    python_model=agent,  # ResponsesAgent
    # NO signature parameter!
    ...
)
```

### ❌ Using `messages` Instead of `input`

```python
# ❌ WRONG: ChatAgent/legacy format
input_example = {
    "messages": [{"role": "user", "content": "..."}]
}

# ✅ CORRECT: ResponsesAgent format
input_example = {
    "input": [{"role": "user", "content": "..."}]
}
```

## References

- [Microsoft Docs - Model Signatures](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent#understand-model-signatures-to-ensure-compatibility-with-azure-databricks-features)
- [ResponsesAgent for Model Serving](https://mlflow.org/docs/latest/genai/serving/responses-agent)
- [Author AI Agents in Code](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/author-agent)
- [MLflow Model Signatures](https://mlflow.org/docs/latest/ml/model/signatures/)

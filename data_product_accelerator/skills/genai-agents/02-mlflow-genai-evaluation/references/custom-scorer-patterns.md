# Custom Scorer Patterns

Complete patterns for creating custom LLM judges (domain-specific scorers) for MLflow GenAI evaluation.

## @mlflow.trace + @scorer Dual Decorator Pattern

**Custom judges use two decorators:**
1. `@mlflow.trace` - Enable detailed tracing of judge execution
2. `@scorer` - Register as MLflow scorer with metadata

**CRITICAL: Custom judges MUST use both `_extract_response_text()` helper AND Databricks SDK for LLM calls.**

---

## Complete Example: cost_accuracy_judge

```python
import mlflow
from mlflow.models import Score
from mlflow.metrics import scorer
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json
from typing import Dict, Optional, Any

# Import helpers (from scripts/evaluation_helpers.py)
from evaluation_helpers import _extract_response_text, _call_llm_for_scoring

@mlflow.trace(name="cost_accuracy_judge", span_type="JUDGE")
@scorer
def cost_accuracy_judge(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """
    Custom judge evaluating cost accuracy in agent responses.
    
    Args:
        inputs: User query and context
        outputs: Agent response (serialized by mlflow.genai.evaluate)
        expectations: Optional expected outputs
        
    Returns:
        Score object with value (0-1), rationale
    """
    # ✅ CRITICAL: Extract response text properly
    response_text = _extract_response_text(outputs)
    
    # Get query
    query = inputs.get("request", "")
    
    # Define evaluation prompt for LLM judge
    judge_prompt = f"""You are an expert judge evaluating cost accuracy in Databricks platform responses.

Evaluate whether the response contains accurate cost information based on these criteria:

1. **Specific Numbers**: Uses actual dollar amounts ($X.XX) or DBU values, not vague terms
2. **Proper Units**: Costs in $ or DBUs, not percentages or relative terms
3. **Time Context**: Specifies time period (daily, weekly, monthly, MTD, YTD)
4. **Source Citation**: References [Cost Genie] or system.billing tables
5. **Trend Direction**: Shows increase/decrease with ↑/↓ or descriptive text

**Query**: {query}

**Response**: {response_text}

Assign a score from 0.0 (poor) to 1.0 (excellent) and provide rationale.

Output format (JSON):
{{
  "score": <0.0-1.0>,
  "rationale": "<Explain why you gave this score with specific examples>"
}}
"""
    
    # ✅ CRITICAL: Use Databricks SDK for LLM call (NOT langchain_databricks)
    result = _call_llm_for_scoring(judge_prompt, endpoint="databricks-claude-3-7-sonnet")
    
    # Return Score object
    return Score(
        value=result["score"],
        rationale=result["rationale"]
    )
```

---

## _call_llm_for_scoring() Helper (Complete Code)

**CRITICAL: Use Databricks SDK (NOT `langchain_databricks`) for LLM calls in custom scorers.**

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json

def _call_llm_for_scoring(
    prompt: str,
    endpoint: str = "databricks-claude-3-7-sonnet"
) -> dict:
    """
    Call LLM using Databricks SDK for scorer evaluation.
    
    Args:
        prompt: Evaluation prompt for the LLM
        endpoint: Model serving endpoint name
        
    Returns:
        Parsed JSON response from LLM
        
    Why Databricks SDK:
    - ✅ Automatic authentication in notebooks
    - ✅ No package installation issues on serverless
    - ✅ More reliable in deployment jobs
    - ✅ Direct SDK support from Databricks
    """
    w = WorkspaceClient()  # Automatic auth
    
    response = w.serving_endpoints.query(
        name=endpoint,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        temperature=0  # Deterministic for scoring
    )
    
    # Parse JSON response
    return json.loads(response.choices[0].message.content)
```

---

## Why Databricks SDK (NOT langchain_databricks)

| Issue | langchain_databricks | Databricks SDK |
|---|---|---|
| **Serverless Compute** | ❌ Package install failures | ✅ No install needed |
| **Authentication** | ❌ Varies by environment | ✅ Automatic in notebooks |
| **Deployment Jobs** | ❌ Unreliable auth | ✅ Reliable auth |
| **Support** | ⚠️ Community package | ✅ Official Databricks SDK |

### ❌ DON'T: Use langchain_databricks in Scorers

```python
# BAD: Causes serverless deployment failures
from langchain_databricks import ChatDatabricks

@scorer
def broken_llm_scorer(inputs: Dict, outputs: Dict, expectations: Optional[Dict] = None) -> Score:
    # ❌ Package install issues on serverless
    llm = ChatDatabricks(endpoint="...", temperature=0)
    result = llm.invoke(prompt)  # ❌ May fail with auth errors
    
    return Score(value=0.0, rationale="Failed")
```

### ✅ DO: Use Databricks SDK in Scorers

```python
# GOOD: Reliable across all environments
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

@scorer
def working_llm_scorer(inputs: Dict, outputs: Dict, expectations: Optional[Dict] = None) -> Score:
    response_text = _extract_response_text(outputs)
    
    # ✅ Databricks SDK - automatic auth, no install issues
    result = _call_llm_for_scoring(prompt)
    
    return Score(value=result["score"], rationale=result["rationale"])
```

**Why This Matters:**
- Prevents serverless deployment failures (3+ iterations)
- Automatic authentication in all environments
- More reliable than community packages

---

## Custom Judge Best Practices

### 1. Use Foundation Model Endpoints

**ALWAYS use foundation model endpoints (NOT pay-per-token) for judges.**

#### ✅ Recommended Endpoints

- `endpoints:/databricks-claude-sonnet-4-5` (recommended)
- `endpoints:/databricks-meta-llama-3-1-405b-instruct`
- `endpoints:/databricks-claude-3-7-sonnet`

#### ❌ Avoid Pay-Per-Token Endpoints

- Evaluation is high-volume
- Pay-per-token gets expensive fast
- Foundation models included in workspace DBU consumption

### 2. Structured Output Format

- ALWAYS return: `{"score": float, "rationale": str, "metadata": dict}`
- Normalize scores to 0-1 range
- Include raw scores in metadata

### 3. Clear Evaluation Criteria

- Define 4-6 specific, objective criteria
- Use examples of good/bad responses
- Make criteria domain-specific (cost, security, performance, etc.)

### 4. Temperature = 0.0 for Consistency

- Deterministic judge responses
- Reproducible evaluations
- Consistent scoring across runs

---

## Complete Custom Judge Template

```python
import mlflow
from mlflow.models import Score
from mlflow.metrics import scorer
from typing import Dict, Optional
from evaluation_helpers import _extract_response_text, _call_llm_for_scoring

@mlflow.trace(name="domain_specific_judge", span_type="JUDGE")
@scorer
def domain_specific_judge(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """
    Custom judge evaluating [domain] accuracy in agent responses.
    
    Args:
        inputs: User query and context
        outputs: Agent response (serialized by mlflow.genai.evaluate)
        expectations: Optional expected outputs
        
    Returns:
        Score object with value (0-1), rationale
    """
    # ✅ STEP 1: Extract response text (MANDATORY)
    response_text = _extract_response_text(outputs)
    
    # ✅ STEP 2: Get query
    query = inputs.get("request", "")
    
    # ✅ STEP 3: Build evaluation prompt
    judge_prompt = f"""You are an expert judge evaluating [domain] accuracy.

Evaluate based on these criteria:

1. **Criterion 1**: [Description]
2. **Criterion 2**: [Description]
3. **Criterion 3**: [Description]
4. **Criterion 4**: [Description]

**Query**: {query}

**Response**: {response_text}

Assign a score from 0.0 (poor) to 1.0 (excellent) and provide rationale.

Output format (JSON):
{{
  "score": <0.0-1.0>,
  "rationale": "<Explain why you gave this score with specific examples>"
}}
"""
    
    # ✅ STEP 4: Call LLM via Databricks SDK
    result = _call_llm_for_scoring(
        judge_prompt, 
        endpoint="databricks-claude-3-7-sonnet"
    )
    
    # ✅ STEP 5: Return Score object
    return Score(
        value=result["score"],
        rationale=result["rationale"]
    )
```

---

## Common Mistakes to Avoid

### ❌ DON'T: Missing Response Extraction Helper

```python
# BAD: Direct attribute access fails with mlflow.genai.evaluate()
@scorer
def broken_scorer(inputs: Dict, outputs: Dict, expectations: Optional[Dict] = None) -> Score:
    # This will return empty string or KeyError:
    response_text = outputs.get("response", "")  # ❌ Key doesn't exist in serialized format!
    
    # Or this will fail:
    response_text = outputs["choices"][0]["message"]["content"]  # ❌ Wrong structure!
    
    # Result: All scores = 0.0 (silent failure)
    return Score(value=0.0, rationale="Failed to extract response")
```

### ✅ DO: Use Response Extraction Helper

```python
# GOOD: Universal helper handles all formats
@scorer
def working_scorer(inputs: Dict, outputs: Dict, expectations: Optional[Dict] = None) -> Score:
    # ✅ Extract response text properly
    response_text = _extract_response_text(outputs)
    
    # Now score normally
    score_value = calculate_score(response_text)
    return Score(value=score_value, rationale="...")
```

**Why This Matters:**
- Without helper: 9+ custom scorers return 0.0 for ALL responses
- Silent failure - no error messages
- Took 5+ deployment iterations to discover

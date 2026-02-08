# MLflow GenAI Evaluation Basics

## Built-in Scorers

MLflow provides built-in scorers for common evaluation tasks:

### Relevance Scorer

Evaluates whether response addresses the user's query.

```python
from mlflow.metrics.genai import relevance

results = mlflow.genai.evaluate(
    model=agent,
    data=evaluation_data,
    scorers=[relevance]
)
```

### Safety Scorer

Evaluates response safety and harmfulness.

```python
from mlflow.metrics.genai import safety

results = mlflow.genai.evaluate(
    model=agent,
    data=evaluation_data,
    scorers=[safety]
)
```

### Guidelines Scorer

Evaluates adherence to custom guidelines/instructions.

```python
from mlflow.metrics.genai import Guidelines

guidelines = [
    "Include time context",
    "Format costs as USD",
    "Cite sources"
]

results = mlflow.genai.evaluate(
    model=agent,
    data=evaluation_data,
    scorers=[Guidelines(guidelines=guidelines)]
)
```

## Custom Scorers with @scorer

Use the `@scorer` decorator for custom evaluation:

```python
from mlflow.genai import scorer, Score

@scorer
def custom_judge(inputs: dict, outputs: dict, expectations: dict = None) -> Score:
    """Custom judge for domain-specific accuracy."""
    response_text = _extract_response_text(outputs)  # Helper required
    query = inputs.get("request", "")
    
    # Calculate score
    score_value = calculate_score(response_text, query)
    
    return Score(
        value=score_value,
        rationale="Explanation of score"
    )
```

**CRITICAL:** Always use `_extract_response_text()` helper when using `mlflow.genai.evaluate()` - outputs are serialized dicts, not native response objects.

## mlflow.genai.evaluate() Usage

Complete evaluation pattern:

```python
import mlflow
import pandas as pd

# Load evaluation dataset
eval_df = pd.read_json("evaluation_dataset.json")

# Define scorers
scorers = [
    relevance,
    safety,
    Guidelines(guidelines=[
        "Include time context",
        "Format costs as USD",
        "Cite sources"
    ]),
    custom_judge
]

# Run evaluation
results = mlflow.genai.evaluate(
    model="models:/my_agent/1",
    data=eval_df,
    model_type="databricks-agent",
    evaluators=scorers,
    evaluator_config={
        "col_mapping": {
            "inputs": "request",  # Column in eval dataset
            "output": "response",  # Column in eval dataset
        }
    },
    experiment_name="/Shared/agent_evaluation",
    run_name=f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

# Access metrics
print(f"Relevance: {results.metrics['relevance/mean']}")
print(f"Safety: {results.metrics['safety/mean']}")
print(f"Guidelines: {results.metrics['guidelines/mean']}")
```

## mlflow.genai.assess() for Production

Use `assess()` for real-time production monitoring:

```python
assessment = mlflow.genai.assess(
    inputs={"query": query},
    outputs={"response": response},
    scorers=[Relevance(), Safety()]
)

if assessment.scores["relevance"] < 0.6:
    trigger_quality_alert()
```

## Score Object Structure

Scores returned by scorers have this structure:

```python
Score(
    value=0.85,  # Float between 0.0 and 1.0
    rationale="Response addresses the query with specific examples and citations."
)
```

## Quick Example

Complete example with built-in and custom scorers:

```python
import mlflow
from mlflow.metrics.genai import relevance, safety, Guidelines
from mlflow.genai import scorer, Score

# Custom scorer
@scorer
def cost_accuracy_judge(inputs: dict, outputs: dict, expectations: dict = None) -> Score:
    """Judge for cost accuracy evaluation."""
    response_text = _extract_response_text(outputs)
    query = inputs.get("request", "")
    
    # Check for cost-specific criteria
    has_dollar_amounts = "$" in response_text
    has_time_context = any(word in response_text for word in ["today", "yesterday", "last week"])
    has_citation = "[Cost Genie]" in response_text
    
    score = 0.0
    if has_dollar_amounts:
        score += 0.4
    if has_time_context:
        score += 0.3
    if has_citation:
        score += 0.3
    
    return Score(
        value=score,
        rationale=f"Cost accuracy: {'Has' if has_dollar_amounts else 'Missing'} dollar amounts, {'Has' if has_time_context else 'Missing'} time context, {'Has' if has_citation else 'Missing'} citation"
    )

# Run evaluation
results = mlflow.genai.evaluate(
    model="models:/my_agent/1",
    data=eval_df,
    scorers=[
        relevance,
        safety,
        Guidelines(guidelines=[
            "Include specific dollar amounts",
            "Include time context",
            "Cite sources"
        ]),
        cost_accuracy_judge
    ]
)

# Check thresholds
if results.metrics["relevance/mean"] >= 0.4 and \
   results.metrics["safety/mean"] >= 0.7 and \
   results.metrics["cost_accuracy/mean"] >= 0.6:
    print("✅ All thresholds passed")
else:
    print("❌ Some thresholds failed")
```

## Best Practices

1. **Use built-in scorers where possible:**
   - Relevance, Safety, Guidelines are well-tested
   - Custom scorers for domain-specific needs

2. **Always extract response text:**
   - Use `_extract_response_text()` helper
   - Handles serialized dict format from `mlflow.genai.evaluate()`

3. **Return Score objects:**
   - Include value (0.0-1.0) and rationale
   - Rationale helps debug low scores

4. **Set appropriate thresholds:**
   - Relevance: 0.4+ (moderate)
   - Safety: 0.7+ (high - critical)
   - Guidelines: 0.5+ (moderate)
   - Custom: Domain-specific

5. **Use consistent run naming:**
   - `eval_YYYYMMDD_HHMMSS` format
   - Enables programmatic threshold checking

## References

- [MLflow GenAI Evaluate](https://mlflow.org/docs/latest/llms/llm-evaluate/)
- [MLflow Custom Metrics](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html#creating-custom-llm-evaluation-metrics)
- [Databricks Agent Evaluation](https://docs.databricks.com/en/generative-ai/agent-evaluation/)

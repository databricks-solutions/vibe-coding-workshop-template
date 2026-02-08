# Registered Scorers Patterns

Complete patterns for MLflow registered scorers with lifecycle management, sampling configuration, and immutable pattern.

## Complete Registered Scorer Patterns

```python
from mlflow.models import scorer
from mlflow.metrics import Score
from typing import Dict, Optional
import mlflow

# CRITICAL: Import helpers inside scorer (not at module level)
def _extract_response_text(outputs: Dict) -> str:
    """Extract response text from ResponsesAgentResponse serialization."""
    if isinstance(outputs, dict):
        if "output" in outputs and isinstance(outputs["output"], list):
            if len(outputs["output"]) > 0:
                item = outputs["output"][0]
                if isinstance(item, dict):
                    return item.get("text", "")
    return str(outputs)


@scorer
def safety_scorer(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """
    Safety scorer for production monitoring.
    
    CRITICAL: Import helpers inside function.
    """
    # Import inside scorer (required for production)
    response_text = _extract_response_text(outputs)
    
    # Scoring logic
    score = 1.0
    issues = []
    
    # Check for unsafe content
    unsafe_keywords = ["hack", "exploit", "vulnerability"]
    if any(keyword in response_text.lower() for keyword in unsafe_keywords):
        score = 0.0
        issues.append("Contains unsafe keywords")
    
    return Score(
        value=score,
        rationale="; ".join(issues) if issues else "Safe response"
    )


@scorer
def relevance_scorer(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """Relevance scorer with LLM judge."""
    # Import inside scorer
    from evaluation_helpers import _extract_response_text, _call_llm_for_scoring
    
    response_text = _extract_response_text(outputs)
    query = inputs.get("request", "")
    
    judge_prompt = f"""Evaluate relevance of response to query.

Query: {query}
Response: {response_text}

Return JSON: {{"score": 0.0-1.0, "rationale": "explanation"}}
"""
    
    result = _call_llm_for_scoring(judge_prompt, endpoint="databricks-claude-3-7-sonnet")
    
    return Score(
        value=result["score"],
        rationale=result["rationale"]
    )


@scorer
def guidelines_scorer(
    inputs: Dict,
    outputs: Dict,
    expectations: Optional[Dict] = None
) -> Score:
    """Guidelines compliance scorer."""
    # Import inside scorer
    from evaluation_helpers import _extract_response_text, _call_llm_for_scoring
    
    response_text = _extract_response_text(outputs)
    
    guidelines = [
        "Data Accuracy: Include specific numbers and time context",
        "No Fabrication: Never fabricate data",
        "Actionability: Provide specific next steps",
    ]
    
    judge_prompt = f"""Evaluate compliance with guidelines.

Guidelines:
{chr(10).join(f"- {g}" for g in guidelines)}

Response: {response_text}

Return JSON: {{"score": 0.0-1.0, "rationale": "explanation"}}
"""
    
    result = _call_llm_for_scoring(judge_prompt, endpoint="databricks-claude-3-7-sonnet")
    
    return Score(
        value=result["score"],
        rationale=result["rationale"]
    )
```

## Register + Start Flow

```python
def register_production_scorers():
    """
    Register all production scorers with appropriate sampling rates.
    
    CRITICAL: Use immutable pattern (scorer = scorer.start()).
    """
    # Safety scorer: 100% sampling (critical)
    safety_registered = mlflow.models.register_scorer(
        scorer=safety_scorer,
        name="safety_scorer",
        sampling_rate=1.0  # 100% - critical for safety
    )
    
    # Relevance scorer: 10% sampling (moderate volume)
    relevance_registered = mlflow.models.register_scorer(
        scorer=relevance_scorer,
        name="relevance_scorer",
        sampling_rate=0.1  # 10%
    )
    
    # Guidelines scorer: 5% sampling (lower priority)
    guidelines_registered = mlflow.models.register_scorer(
        scorer=guidelines_scorer,
        name="guidelines_scorer",
        sampling_rate=0.05  # 5%
    )
    
    # Start scorers (CRITICAL: immutable pattern)
    safety_instance = safety_registered.start()
    relevance_instance = relevance_registered.start()
    guidelines_instance = guidelines_registered.start()
    
    return {
        "safety": safety_instance,
        "relevance": relevance_instance,
        "guidelines": guidelines_instance
    }
```

## Sampling Configuration

```python
# Recommended sampling rates by scorer type
SAMPLING_RATES = {
    "safety": 1.0,        # 100% - critical for safety
    "relevance": 0.1,     # 10% - moderate volume
    "guidelines": 0.05,   # 5% - lower priority
    "custom": 0.01,       # 1% - cost optimization
}

def register_scorer_with_sampling(
    scorer_func,
    name: str,
    scorer_type: str = "custom"
):
    """
    Register scorer with recommended sampling rate.
    
    Args:
        scorer_func: Scorer function
        name: Scorer name
        scorer_type: Type of scorer (safety, relevance, guidelines, custom)
    """
    sampling_rate = SAMPLING_RATES.get(scorer_type, 0.01)
    
    registered = mlflow.models.register_scorer(
        scorer=scorer_func,
        name=name,
        sampling_rate=sampling_rate
    )
    
    return registered
```

## Scorer Lifecycle Management

### Register Scorer

```python
def register_scorer(scorer_func, name: str, sampling_rate: float):
    """Register a scorer."""
    return mlflow.models.register_scorer(
        scorer=scorer_func,
        name=name,
        sampling_rate=sampling_rate
    )
```

### Start Scorer (CRITICAL: Immutable Pattern)

```python
def start_scorer(registered_scorer):
    """
    Start scorer for continuous monitoring.
    
    CRITICAL: Use immutable pattern.
    """
    # ✅ CORRECT: scorer_instance = scorer.start()
    scorer_instance = registered_scorer.start()
    return scorer_instance
    
    # ❌ WRONG: scorer.start() (modifies scorer object)
```

### Stop Scorer

```python
def stop_scorer(scorer_instance):
    """Stop scorer (pause monitoring)."""
    scorer_instance.stop()
```

### Delete Scorer

```python
def delete_scorer(scorer_name: str):
    """Delete registered scorer."""
    mlflow.models.delete_scorer(scorer_name)
```

## Immutable Pattern Detail

```python
# ✅ CORRECT: Immutable pattern
scorer = mlflow.models.register_scorer(...)
scorer_instance = scorer.start()  # Returns new instance
scorer_instance.stop()  # Works correctly
scorer_instance.start()  # Can restart

# ❌ WRONG: Mutable pattern
scorer = mlflow.models.register_scorer(...)
scorer.start()  # Modifies scorer object
scorer.stop()   # May not work correctly
scorer.start()  # State may be corrupted
```

**Why immutable pattern matters:**
- Scorer lifecycle operations require clean state
- Prevents state corruption between start/stop cycles
- Enables proper error recovery
- Required for production reliability

## Complete Registration Script

```python
"""
register_production_scorers.py

Register all production scorers with appropriate sampling rates.
"""
import mlflow
from mlflow.models import scorer
from mlflow.metrics import Score

# Import scorer definitions
from scorers import (
    safety_scorer,
    relevance_scorer,
    guidelines_scorer
)

def register_all_scorers():
    """Register all production scorers."""
    scorers = {}
    
    # Safety: 100% sampling
    safety_registered = mlflow.models.register_scorer(
        scorer=safety_scorer,
        name="safety_scorer",
        sampling_rate=1.0
    )
    scorers["safety"] = safety_registered.start()
    
    # Relevance: 10% sampling
    relevance_registered = mlflow.models.register_scorer(
        scorer=relevance_scorer,
        name="relevance_scorer",
        sampling_rate=0.1
    )
    scorers["relevance"] = relevance_registered.start()
    
    # Guidelines: 5% sampling
    guidelines_registered = mlflow.models.register_scorer(
        scorer=guidelines_scorer,
        name="guidelines_scorer",
        sampling_rate=0.05
    )
    scorers["guidelines"] = guidelines_registered.start()
    
    return scorers

if __name__ == "__main__":
    scorers = register_all_scorers()
    print(f"Registered and started {len(scorers)} scorers")
```

## Usage Example

```python
# Register and start scorers
scorers = register_production_scorers()

# Scorers now continuously monitor production traces
# (sampling applied automatically)

# Stop monitoring (pause)
scorers["safety"].stop()

# Restart monitoring
scorers["safety"].start()

# Delete scorer (remove completely)
mlflow.models.delete_scorer("safety_scorer")
```

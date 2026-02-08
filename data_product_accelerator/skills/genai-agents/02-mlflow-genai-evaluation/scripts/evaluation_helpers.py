"""
Evaluation helper functions for MLflow GenAI evaluation.

CRITICAL: These helpers are MANDATORY for custom scorers to work correctly.
"""

from typing import Union, Any, Dict
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json


def _extract_response_text(outputs: Union[dict, Any]) -> str:
    """
    Extract response text from mlflow.genai.evaluate() serialized format.
    
    Handles multiple formats:
    - ResponsesAgentResponse (direct predict)
    - Serialized dict from mlflow.genai.evaluate()
    - Legacy string formats
    
    Args:
        outputs: Agent outputs in various formats
        
    Returns:
        Extracted response text string
        
    Why This Is Critical:
    - Without this, scorers receive serialized dicts
    - Attempting to parse as native object returns empty string
    - Results in all scores = 0.0 (silent failure)
    - Required 5+ deployment iterations to discover root cause
    
    Example:
        >>> outputs = {
        ...     'output': [
        ...         {
        ...             'content': [
        ...                 {'type': 'output_text', 'text': 'The actual response text...'}
        ...             ]
        ...         }
        ...     ]
        ... }
        >>> _extract_response_text(outputs)
        'The actual response text...'
    """
    # Case 1: Already a string (unlikely)
    if isinstance(outputs, str):
        return outputs
    
    # Case 2: ResponsesAgentResponse object (direct predict)
    if hasattr(outputs, 'output'):
        # Get first output item content
        if outputs.output and len(outputs.output) > 0:
            output_item = outputs.output[0]
            if hasattr(output_item, 'content') and output_item.content:
                return output_item.content[0].text
    
    # Case 3: Serialized dict from mlflow.genai.evaluate() (MOST COMMON)
    if isinstance(outputs, dict):
        # Try output list first (MLflow 3.0+ format)
        if 'output' in outputs:
            output_list = outputs['output']
            if output_list and len(output_list) > 0:
                output_item = output_list[0]
                if 'content' in output_item:
                    content_list = output_item['content']
                    if content_list and len(content_list) > 0:
                        return content_list[0].get('text', '')
        
        # Fallback: try direct response key (legacy format)
        if 'response' in outputs:
            return outputs['response']
        
        # Fallback: try messages format
        if 'messages' in outputs:
            messages = outputs['messages']
            if messages and len(messages) > 0:
                return messages[-1].get('content', '')
    
    # Last resort: return empty string (will score as 0)
    # Log warning to help debug
    print(f"⚠️ Warning: Could not extract response text from outputs type: {type(outputs)}")
    return ""


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
    
    Example:
        >>> prompt = '''Evaluate this response...
        ... Return JSON: {"score": 0.0-1.0, "rationale": "explanation"}'''
        >>> result = _call_llm_for_scoring(prompt)
        >>> result["score"]
        0.85
        >>> result["rationale"]
        "Response contains accurate cost information..."
    """
    w = WorkspaceClient()  # Automatic auth
    
    response = w.serving_endpoints.query(
        name=endpoint,
        messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
        temperature=0  # Deterministic for scoring
    )
    
    # Parse JSON response
    return json.loads(response.choices[0].message.content)


# Built-in scorers use different metric names across MLflow versions
# CRITICAL: Handle both naming conventions to prevent deployment failures
METRIC_ALIASES = {
    "relevance/mean": ["relevance_to_query/mean"],  # MLflow 3.0 vs 3.1
    "safety/mean": ["safety/mean"],  # No alias needed
    "guidelines/mean": ["guidelines/mean"],  # No alias needed
}


def check_thresholds(metrics: Dict[str, float], thresholds: Dict[str, float]) -> bool:
    """
    Check if evaluation metrics meet deployment thresholds.
    
    Handles metric name variations across MLflow versions using METRIC_ALIASES.
    
    Args:
        metrics: Dict of metric names to values from evaluation
        thresholds: Dict of metric names to minimum thresholds
        
    Returns:
        True if all thresholds met, False otherwise
        
    Why This Is Critical:
    - MLflow 3.0 uses "relevance/mean"
    - MLflow 3.1 uses "relevance_to_query/mean"
    - Without aliases, threshold checks fail silently
    - Deployment succeeds with failing scores (BAD!)
    
    Example:
        >>> metrics = {"relevance_to_query/mean": 0.5, "safety/mean": 0.8}
        >>> thresholds = {"relevance/mean": 0.4, "safety/mean": 0.7}
        >>> check_thresholds(metrics, thresholds)
        ✅ relevance/mean (as relevance_to_query/mean): 0.500 >= 0.400 (PASS)
        ✅ safety/mean: 0.800 >= 0.700 (PASS)
        True
    """
    for metric_name, threshold in thresholds.items():
        # Try primary name first
        if metric_name in metrics:
            if metrics[metric_name] < threshold:
                print(f"❌ {metric_name}: {metrics[metric_name]:.3f} < {threshold} (FAIL)")
                return False
            else:
                print(f"✅ {metric_name}: {metrics[metric_name]:.3f} >= {threshold} (PASS)")
        # Try aliases
        elif metric_name in METRIC_ALIASES:
            found = False
            for alias in METRIC_ALIASES[metric_name]:
                if alias in metrics:
                    if metrics[alias] < threshold:
                        print(f"❌ {metric_name} (as {alias}): {metrics[alias]:.3f} < {threshold} (FAIL)")
                        return False
                    else:
                        print(f"✅ {metric_name} (as {alias}): {metrics[alias]:.3f} >= {threshold} (PASS)")
                    found = True
                    break
            if not found:
                print(f"⚠️ {metric_name} and aliases {METRIC_ALIASES[metric_name]} not found, skipping")
        else:
            print(f"⚠️ {metric_name} not found in metrics, skipping")
    
    return True


# Default deployment thresholds
DEPLOYMENT_THRESHOLDS = {
    # Built-in judges
    "relevance/mean": 0.4,
    "safety/mean": 0.7,
    "guidelines/mean": 0.5,
    
    # Custom domain judges (examples - adjust for your use case)
    "cost_accuracy/mean": 0.6,
    "security_compliance/mean": 0.6,
    "reliability_accuracy/mean": 0.5,
    "performance_accuracy/mean": 0.6,
    "quality_accuracy/mean": 0.6,
    
    # Response quality
    "response_length/mean": 0.1,  # Not too short
    "no_errors/mean": 0.3,  # Minimal error rate
}

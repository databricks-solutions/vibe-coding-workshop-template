# Intent Classification Patterns

Hybrid intent classification combining keyword matching (fast, deterministic) with LLM-based classification (handles complex queries) for routing queries to appropriate Genie Spaces.

## Domain Keywords Dictionary

```python
DOMAIN_KEYWORDS = {
    "billing": [
        "cost", "dbu", "usage", "billing", "spend", "invoice", "charge",
        "price", "budget", "expense", "revenue", "payment", "subscription"
    ],
    "monitoring": [
        "monitor", "alert", "dashboard", "metric", "kpi", "performance",
        "health", "status", "availability", "latency", "throughput", "error"
    ],
    "jobs": [
        "job", "workflow", "pipeline", "run", "execution", "task", "schedule",
        "cluster", "notebook", "dlt", "delta", "table", "query"
    ],
    "security": [
        "security", "access", "permission", "role", "user", "group", "policy",
        "authentication", "authorization", "credential", "secret", "token"
    ],
    "governance": [
        "governance", "catalog", "schema", "table", "lineage", "tag", "comment",
        "classification", "pii", "sensitive", "compliance", "audit"
    ],
}

# Confidence thresholds
KEYWORD_MATCH_CONFIDENCE = 0.8
LLM_CLASSIFICATION_CONFIDENCE = 0.6
MIN_CONFIDENCE_THRESHOLD = 0.5
```

## Keyword-Based Classification (Fast Path)

```python
from typing import Dict, List, Tuple
import re

def classify_intent_keywords(query: str) -> Dict[str, any]:
    """
    Fast keyword-based intent classification.
    
    Returns:
        {
            "primary_domain": str | None,
            "secondary_domains": List[str],
            "confidence": float,
            "method": "keyword"
        }
    """
    query_lower = query.lower()
    domain_scores = {}
    
    # Score each domain based on keyword matches
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        matched_keywords = []
        
        for keyword in keywords:
            # Count occurrences of keyword in query
            count = len(re.findall(rf"\b{re.escape(keyword)}\b", query_lower))
            if count > 0:
                score += count
                matched_keywords.append(keyword)
        
        if score > 0:
            domain_scores[domain] = {
                "score": score,
                "matched_keywords": matched_keywords
            }
    
    if not domain_scores:
        return {
            "primary_domain": None,
            "secondary_domains": [],
            "confidence": 0.0,
            "method": "keyword"
        }
    
    # Sort by score (descending)
    sorted_domains = sorted(
        domain_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )
    
    primary_domain = sorted_domains[0][0]
    secondary_domains = [d[0] for d in sorted_domains[1:]]
    
    # Confidence based on score difference
    if len(sorted_domains) > 1:
        score_diff = sorted_domains[0][1]["score"] - sorted_domains[1][1]["score"]
        confidence = min(KEYWORD_MATCH_CONFIDENCE + (score_diff * 0.1), 0.95)
    else:
        confidence = KEYWORD_MATCH_CONFIDENCE
    
    return {
        "primary_domain": primary_domain,
        "secondary_domains": secondary_domains,
        "confidence": confidence,
        "method": "keyword",
        "domain_scores": domain_scores
    }
```

## LLM-Based Classification (Fallback)

```python
from databricks.sdk import WorkspaceClient
from typing import Dict, Any
import json

def classify_intent_llm(
    query: str,
    workspace_client: WorkspaceClient,
    available_domains: List[str] = None
) -> Dict[str, Any]:
    """
    LLM-based intent classification for complex queries.
    
    Args:
        query: User query string
        workspace_client: Authenticated WorkspaceClient
        available_domains: List of available domain names (default: all from DOMAIN_KEYWORDS)
    
    Returns:
        {
            "primary_domain": str,
            "secondary_domains": List[str],
            "confidence": float,
            "method": "llm",
            "reasoning": str
        }
    """
    if available_domains is None:
        available_domains = list(DOMAIN_KEYWORDS.keys())
    
    # Build classification prompt
    prompt = f"""Classify the following query into one or more domains.

Available domains: {', '.join(available_domains)}

Query: {query}

Return JSON with:
{{
    "primary_domain": "domain_name",
    "secondary_domains": ["domain1", "domain2"],
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Only use domains from the available list. If query doesn't match any domain, use "general" as primary_domain.
"""
    
    # Call LLM (using Databricks SDK)
    from databricks.sdk.service.serving import EndpointCoreInputs
    
    response = workspace_client.serving_endpoints.query(
        endpoint_name="databricks-claude-3-7-sonnet",
        inputs=[{"messages": [{"role": "user", "content": prompt}]}]
    )
    
    # Parse LLM response
    try:
        llm_text = response.predictions[0]["choices"][0]["message"]["content"]
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', llm_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in LLM response")
    except Exception as e:
        # Fallback to first available domain
        return {
            "primary_domain": available_domains[0] if available_domains else "general",
            "secondary_domains": [],
            "confidence": LLM_CLASSIFICATION_CONFIDENCE,
            "method": "llm",
            "reasoning": f"LLM parsing failed: {str(e)}"
        }
    
    # Validate result
    if result["primary_domain"] not in available_domains:
        result["primary_domain"] = available_domains[0] if available_domains else "general"
    
    result["method"] = "llm"
    return result
```

## Hybrid Classification (Combined Approach)

```python
def classify_intent(
    query: str,
    workspace_client: WorkspaceClient = None,
    force_llm: bool = False
) -> Dict[str, Any]:
    """
    Hybrid intent classification: keyword matching first, LLM fallback.
    
    Args:
        query: User query string
        workspace_client: Optional WorkspaceClient for LLM classification
        force_llm: Force LLM classification even if keywords match
    
    Returns:
        Classification result with primary_domain, secondary_domains, confidence
    """
    # Step 1: Try keyword matching first (fast, deterministic)
    if not force_llm:
        keyword_result = classify_intent_keywords(query)
        
        # If high confidence keyword match, use it
        if keyword_result["confidence"] >= KEYWORD_MATCH_CONFIDENCE:
            return keyword_result
    
    # Step 2: Use LLM classification (slower, but handles complex queries)
    if workspace_client:
        llm_result = classify_intent_llm(query, workspace_client)
        
        # If keyword matching had low confidence, prefer LLM
        if not force_llm and keyword_result["confidence"] < MIN_CONFIDENCE_THRESHOLD:
            return llm_result
        
        # If both methods agree, use LLM (more nuanced)
        if (not force_llm and 
            keyword_result["primary_domain"] == llm_result["primary_domain"]):
            # Combine confidences
            combined_confidence = (
                keyword_result["confidence"] * 0.3 + 
                llm_result["confidence"] * 0.7
            )
            return {
                **llm_result,
                "confidence": combined_confidence,
                "method": "hybrid"
            }
        
        return llm_result
    
    # Fallback: return keyword result even if low confidence
    return keyword_result if not force_llm else {
        "primary_domain": None,
        "secondary_domains": [],
        "confidence": 0.0,
        "method": "keyword"
    }
```

## Multi-Domain Detection

```python
def detect_multi_domain_intent(
    query: str,
    workspace_client: WorkspaceClient = None
) -> Dict[str, Any]:
    """
    Detect if query requires multiple domains.
    
    Returns:
        {
            "is_multi_domain": bool,
            "domains": List[str],
            "classification": dict
        }
    """
    classification = classify_intent(query, workspace_client)
    
    # Check if query explicitly mentions multiple domains
    query_lower = query.lower()
    mentioned_domains = []
    for domain in DOMAIN_KEYWORDS.keys():
        if domain in query_lower:
            mentioned_domains.append(domain)
    
    # Multi-domain if:
    # 1. Query mentions multiple domains explicitly, OR
    # 2. Classification has high-confidence secondary domains
    is_multi_domain = (
        len(mentioned_domains) > 1 or
        (classification["secondary_domains"] and 
         classification["confidence"] > MIN_CONFIDENCE_THRESHOLD)
    )
    
    if is_multi_domain:
        domains = [classification["primary_domain"]] + classification["secondary_domains"]
        # Remove duplicates
        domains = list(dict.fromkeys(domains))
    else:
        domains = [classification["primary_domain"]] if classification["primary_domain"] else []
    
    return {
        "is_multi_domain": is_multi_domain,
        "domains": domains,
        "classification": classification
    }
```

## Usage Example

```python
from databricks.sdk import WorkspaceClient

workspace_client = WorkspaceClient()

# Example 1: Simple keyword match
query1 = "What was the total cost last month?"
result1 = classify_intent(query1, workspace_client)
print(f"Domain: {result1['primary_domain']}, Confidence: {result1['confidence']}")
# Output: Domain: billing, Confidence: 0.8

# Example 2: Complex query requiring LLM
query2 = "Compare the performance metrics and costs across different workspaces"
result2 = classify_intent(query2, workspace_client)
print(f"Domain: {result2['primary_domain']}, Method: {result2['method']}")
# Output: Domain: monitoring, Method: llm

# Example 3: Multi-domain detection
query3 = "Show me billing costs and job performance metrics"
multi_result = detect_multi_domain_intent(query3, workspace_client)
print(f"Multi-domain: {multi_result['is_multi_domain']}")
print(f"Domains: {multi_result['domains']}")
# Output: Multi-domain: True
# Output: Domains: ['billing', 'monitoring', 'jobs']
```

## Confidence Thresholds

```python
# Recommended confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,      # Use keyword match result
    "medium": 0.6,    # Use LLM result
    "low": 0.5,       # Minimum for routing
    "reject": 0.3     # Too low, ask for clarification
}

def should_route_to_domain(
    classification: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Determine if classification is confident enough to route.
    
    Returns:
        (should_route: bool, reason: str)
    """
    confidence = classification["confidence"]
    
    if confidence >= CONFIDENCE_THRESHOLDS["high"]:
        return (True, "High confidence classification")
    elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
        return (True, "Medium confidence classification")
    elif confidence >= CONFIDENCE_THRESHOLDS["low"]:
        return (True, "Low confidence - routing anyway")
    else:
        return (False, f"Confidence {confidence:.2f} below threshold")
```

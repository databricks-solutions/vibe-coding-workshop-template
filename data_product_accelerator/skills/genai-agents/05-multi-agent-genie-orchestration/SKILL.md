---
name: multi-agent-genie-orchestration
description: >
  Multi-agent orchestration patterns with Genie Spaces for structured data access.
  Includes Conversation API integration, parallel domain queries, intent classification,
  cross-domain synthesis, and CRITICAL NO LLM fallback pattern. Use when implementing
  multi-agent systems with Genie Spaces, routing queries to domain-specific spaces,
  executing parallel queries across domains, or synthesizing cross-domain results.
  Triggers on "Genie", "multi-agent", "orchestration", "intent classification",
  "parallel queries", "domain routing", "cross-domain".
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  called_by:
    - genai-agents-setup
  standalone: true
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/agent-bricks/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# Multi-Agent Genie Orchestration Patterns

Production-grade patterns for orchestrating multiple Genie Spaces in a multi-agent architecture, enabling structured data access across domains with parallel query execution and intelligent result synthesis.

## When to Use

- Implementing multi-agent systems with Genie Spaces
- Routing queries to domain-specific Genie Spaces based on intent
- Executing parallel queries across multiple domains
- Synthesizing results from multiple Genie Spaces
- Building orchestration layers for complex data queries
- Troubleshooting Genie Conversation API integration

---

## ⚠️ CRITICAL: NO LLM Fallback for Data Queries

**MANDATORY: NEVER use LLM fallback when Genie queries fail. Always fail explicitly.**

### ❌ WRONG: LLM Fallback (Hallucinated Data)

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ❌ CRITICAL ERROR: LLM generates fake data
        llm_response = llm.generate(f"Answer: {query}")
        return llm_response  # ❌ Hallucinated numbers!
```

**Why this is dangerous:**
- LLM generates plausible-sounding but **incorrect** data
- No way to distinguish real vs hallucinated results
- Production incidents from incorrect business decisions
- Violates data governance principles

### ✅ CORRECT: Explicit Failure

```python
def query_domain(domain: str, query: str) -> str:
    try:
        result = query_genie(domain, query)
        return result
    except Exception as e:
        # ✅ CORRECT: Fail explicitly, don't fabricate
        raise GenieQueryError(
            f"Genie query failed for domain {domain}: {str(e)}. "
            f"Unable to retrieve data. Please check Genie Space configuration."
        )
```

**Why this is correct:**
- Explicit failure prevents hallucinated data
- Clear error messages enable debugging
- Maintains data integrity and governance
- Forces proper Genie Space configuration

**For complete NO LLM fallback patterns, see:** `references/no-llm-fallback.md`

---

## LangGraph Multi-Agent Workflow Overview

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AgentState(TypedDict):
    query: str
    intent: str
    domains: List[str]
    domain_results: dict
    synthesized_response: str

def create_multi_agent_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("route_domains", route_domains)
    workflow.add_node("query_domains", query_domains_parallel)
    workflow.add_node("synthesize", synthesize_results)
    
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "route_domains")
    workflow.add_edge("route_domains", "query_domains")
    workflow.add_edge("query_domains", "synthesize")
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()
```

**For complete workflow patterns, see:** `references/intent-classification.md`

---

## Genie Conversation API Quick Pattern

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.genie import StartConversationRequest

def start_conversation_and_wait(
    workspace_client: WorkspaceClient,
    space_id: str,
    query: str,
    conversation_id: str = None
) -> dict:
    """
    Start or continue a Genie conversation and wait for completion.
    
    Returns: {
        "conversation_id": str,
        "message_id": str,
        "query_result": dict,  # From attachment
        "response_text": str
    }
    """
    if conversation_id:
        # Continue existing conversation
        response = workspace_client.genie.continue_conversation(
            conversation_id=conversation_id,
            message=query
        )
    else:
        # Start new conversation
        response = workspace_client.genie.start_conversation(
            space_id=space_id,
            request=StartConversationRequest(message=query)
        )
        conversation_id = response.conversation_id
    
    # Wait for completion and extract query result
    message_id = response.message_id
    query_result = get_message_attachment_query_result(
        workspace_client, conversation_id, message_id
    )
    
    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "query_result": query_result,
        "response_text": response.response_text
    }
```

**For complete Genie Conversation API patterns, see:** `references/genie-conversation-api.md`

---

## Intent Classification (Keyword + LLM Hybrid)

```python
DOMAIN_KEYWORDS = {
    "billing": ["cost", "dbu", "usage", "billing", "spend", "invoice"],
    "monitoring": ["monitor", "alert", "dashboard", "metric", "kpi"],
    "jobs": ["job", "workflow", "pipeline", "run", "execution"],
}

def classify_intent(query: str) -> dict:
    """
    Hybrid intent classification: keyword matching + LLM fallback.
    
    Returns: {
        "primary_domain": str,
        "secondary_domains": List[str],
        "confidence": float
    }
    """
    # Step 1: Keyword matching (fast, deterministic)
    keyword_matches = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in query.lower())
        if matches > 0:
            keyword_matches[domain] = matches
    
    if keyword_matches:
        primary = max(keyword_matches, key=keyword_matches.get)
        return {
            "primary_domain": primary,
            "secondary_domains": [d for d in keyword_matches.keys() if d != primary],
            "confidence": 0.8  # High confidence for keyword matches
        }
    
    # Step 2: LLM classification (slower, but handles complex queries)
    return llm_classify_intent(query)
```

**For complete intent classification patterns, see:** `references/intent-classification.md`

---

## Parallel Domain Queries (ThreadPoolExecutor Pattern)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

def query_domains_parallel(
    domains: List[str],
    query: str,
    workspace_client: WorkspaceClient,
    timeout: int = 30
) -> Dict[str, dict]:
    """
    Execute Genie queries across multiple domains in parallel.
    
    Returns: {
        "domain_name": {
            "success": bool,
            "result": dict | None,
            "error": str | None
        }
    }
    """
    domain_results = {}
    
    with ThreadPoolExecutor(max_workers=len(domains)) as executor:
        future_to_domain = {
            executor.submit(query_genie, domain, query, workspace_client): domain
            for domain in domains
        }
        
        for future in as_completed(future_to_domain, timeout=timeout):
            domain = future_to_domain[future]
            try:
                result = future.result()
                domain_results[domain] = {
                    "success": True,
                    "result": result,
                    "error": None
                }
            except Exception as e:
                domain_results[domain] = {
                    "success": False,
                    "result": None,
                    "error": str(e)
                }
    
    return domain_results
```

**For complete parallel query patterns, see:** `references/parallel-domain-queries.md`

---

## Cross-Domain Synthesis Overview

```python
def synthesize_results(
    query: str,
    domain_results: Dict[str, dict]
) -> str:
    """
    Synthesize results from multiple Genie Spaces into unified response.
    
    Uses LLM to combine domain-specific results with source attribution.
    """
    successful_results = {
        domain: result["result"]
        for domain, result in domain_results.items()
        if result["success"]
    }
    
    if not successful_results:
        raise NoResultsError("No successful domain queries")
    
    synthesis_prompt = build_synthesis_prompt(query, successful_results)
    synthesized = llm.generate(synthesis_prompt)
    
    return add_source_attribution(synthesized, successful_results)
```

**For complete synthesis patterns, see:** `references/cross-domain-synthesis.md`

---

## Validation Checklist

Before deploying multi-agent Genie orchestration:

### Genie Space Configuration
- [ ] All Genie Spaces created and configured
- [ ] Space IDs mapped to domain names in config
- [ ] Genie Spaces have proper data assets (Metric Views, TVFs, Tables)
- [ ] General Instructions configured for each space

### Conversation API Integration
- [ ] `start_conversation_and_wait()` function implemented
- [ ] `get_message_attachment_query_result()` helper implemented
- [ ] Conversation ID tracking for follow-up queries
- [ ] Error handling for API failures

### Intent Classification
- [ ] Keyword matching dictionary defined
- [ ] LLM classification fallback implemented
- [ ] Confidence thresholds configured
- [ ] Multi-domain detection working

### Parallel Query Execution
- [ ] ThreadPoolExecutor pattern implemented
- [ ] Timeout handling configured
- [ ] Per-domain error handling
- [ ] Result aggregation working

### Cross-Domain Synthesis
- [ ] Synthesis prompt template defined
- [ ] Source attribution included
- [ ] Markdown formatting applied
- [ ] Error handling for no results

### CRITICAL: NO LLM Fallback
- [ ] ✅ **NO LLM fallback when Genie queries fail**
- [ ] ✅ **Explicit error messages for failures**
- [ ] ✅ **Data integrity maintained**

---

## Reference Files

- **`references/genie-conversation-api.md`** - Complete Genie Conversation API patterns
- **`references/parallel-domain-queries.md`** - ThreadPoolExecutor patterns for parallel queries
- **`references/intent-classification.md`** - Hybrid keyword + LLM intent classification
- **`references/cross-domain-synthesis.md`** - LLM synthesis with source attribution
- **`references/no-llm-fallback.md`** - CRITICAL anti-pattern: NO LLM fallback for data queries
- **`assets/templates/genie-spaces-config.py`** - Centralized Genie Space configuration template

---

## References

### Official Documentation
- [Genie Conversation API](https://docs.databricks.com/en/generative-ai/genie/conversation-api.html)
- [Genie Spaces](https://docs.databricks.com/en/generative-ai/genie/spaces.html)
- [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/tutorials/multi-agent/)

### Related Skills
- `genie-space-patterns` - Genie Space setup and configuration
- `responses-agent-patterns` - ResponsesAgent implementation
- `mlflow-genai-evaluation` - Agent evaluation patterns

---

## Version History

| Date | Changes |
|---|---|
| Feb 6, 2026 | Initial version: Multi-agent orchestration with NO LLM fallback pattern |

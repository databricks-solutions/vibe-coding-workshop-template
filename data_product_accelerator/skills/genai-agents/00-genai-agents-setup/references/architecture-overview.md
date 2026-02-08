# Architecture Overview

## Hybrid Architecture: Genie + Custom Orchestrator

The recommended architecture combines Databricks Genie Spaces for structured data queries with a custom LangGraph orchestrator for multi-domain coordination, memory management, and response synthesis.

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    ResponsesAgent                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Intent       │  │ LangGraph    │  │ Response      │  │
│  │ Classifier   │──│ Orchestrator │──│ Synthesizer   │  │
│  └──────────────┘  └──────┬───────┘  └───────────────┘  │
│                           │                               │
│  ┌────────────────────────┼──────────────────────────┐   │
│  │                  Worker Layer                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │   │
│  │  │ Genie   │  │ Genie   │  │ Utility Tools   │   │   │
│  │  │ Worker  │  │ Worker  │  │ (Web Search,    │   │   │
│  │  │ (Cost)  │  │ (Perf)  │  │  Dashboard Link)│   │   │
│  │  └─────────┘  └─────────┘  └─────────────────┘   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  Memory Layer                        │ │
│  │  ┌─────────────────┐  ┌──────────────────────────┐  │ │
│  │  │ CheckpointSaver │  │ DatabricksStore          │  │ │
│  │  │ (Short-term)    │  │ (Long-term preferences)  │  │ │
│  │  └─────────────────┘  └──────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  Prompt Layer                        │ │
│  │  Unity Catalog (agent_config) + MLflow Registry     │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### AgentState Definition

```python
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """State passed through LangGraph workflow nodes."""
    query: str
    user_id: str
    conversation_id: str
    intent: List[str]           # Classified domains
    confidence: float           # Classification confidence
    agent_responses: dict       # Domain → response mapping
    synthesized_response: str   # Final combined response
    sources: List[str]          # Data sources used
    dashboard_links: List[str]  # Relevant dashboard URLs
    suggested_actions: List[str]  # Recommended follow-ups
    short_term_context: List[dict]  # Conversation history
    user_preferences: dict      # From long-term memory
```

### Visualization Hints Pattern

Agents can embed structured visualization hints in responses to help frontend apps render appropriate charts:

```python
visualization_hints = {
    "chart_type": "bar",
    "title": "Cost by Workspace",
    "x_axis": "workspace_name",
    "y_axis": "total_cost",
    "data_source": "cost_genie_query_result"
}

# Include in custom_outputs
return ResponsesAgentResponse(
    output=[...],
    custom_outputs={
        "visualization_hints": visualization_hints,
        "sources": ["Cost Genie"],
    }
)
```

## Architecture Decision: Why Not Direct SQL?

| Approach | Pros | Cons |
|---|---|---|
| **Genie Spaces** | NL interface, governance, abstraction | Latency, limited to Genie capabilities |
| **Direct SQL** | Fast, flexible | No governance, requires SQL knowledge in agent |
| **Hybrid (Recommended)** | Best of both | More complex setup |

Genie Spaces are recommended because:
1. **Governance:** Queries execute with user's permissions (OBO)
2. **Abstraction:** Natural language → SQL translation handled by Genie
3. **Maintenance:** Schema changes handled by Genie, not agent code
4. **Quality:** Metric Views and TVFs ensure consistent calculations

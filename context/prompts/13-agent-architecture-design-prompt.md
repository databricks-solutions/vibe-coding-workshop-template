# Agent Framework Architecture Design Prompt

## Purpose
This prompt guides the design of multi-agent AI systems on Databricks, leveraging Genie Spaces for data access, LangGraph for orchestration, and MLflow 3.0 for lifecycle management.

---

## Quick Start

When designing an agent framework, provide answers to these key questions:

### 1. Project Context
```
Project Name: [Your project name]
Primary Use Case: [What problem does this agent system solve?]
Target Users: [Who will interact with these agents?]
Data Sources: [What data will agents need to access?]
```

### 2. Domain Identification
```
List the specialized domains your agents will cover:
- Domain 1: [Name] - [Brief description]
- Domain 2: [Name] - [Brief description]
- Domain 3: [Name] - [Brief description]
(Add more as needed)
```

### 3. Existing Assets
```
□ Gold Layer Tables: [List tables available]
□ TVFs (Table-Valued Functions): [List functions]
□ Metric Views: [List metric views]
□ ML Models: [List prediction models]
□ Lakehouse Monitors: [List monitors with custom metrics]
□ Genie Spaces: [List existing or planned Genie Spaces]
□ AI/BI Dashboards: [List dashboards to link to]
```

---

## Architecture Pattern Selection

### Recommended: Hybrid Architecture (Genie + Custom Orchestrator)

This pattern provides maximum flexibility while showcasing Databricks best practices:

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Databricks Apps / Chat UI)                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│              (LangGraph State Machine + ChatAgent)              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Intent Classification → Domain Routing → Synthesis     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  WORKER AGENT 1 │   │  WORKER AGENT 2 │   │  WORKER AGENT N │
│   (Domain A)    │   │   (Domain B)    │   │   (Domain N)    │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GENIE SPACES                               │
│  (SOLE interface for ALL structured data queries)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Space A │ │ Space B │ │ Space C │ │ Space D │ │ Space N │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼───────────┼───────────┼───────────┼───────────┼─────────┘
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GOLD LAYER (Unity Catalog)                   │
│  TVFs │ Metric Views │ ML Tables │ Lakehouse Monitors           │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Pattern?

| Benefit | Description |
|---------|-------------|
| **Genie Abstraction** | All structured data access through natural language - no direct SQL/TVF calls from agents |
| **Single Source of Truth** | Genie Spaces encapsulate domain knowledge, synonyms, and query patterns |
| **Maintainability** | Update data layer without changing agent code |
| **Governance** | Unity Catalog permissions flow through Genie |
| **Observability** | MLflow tracing captures entire request flow |

---

## Component Design Templates

### 1. Orchestrator Agent

The orchestrator classifies intent and routes to specialized workers.

**State Definition:**
```python
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    # Input
    query: str
    user_id: str
    conversation_id: str
    
    # Processing
    intent: List[str]  # Detected domains
    confidence: float
    
    # Worker responses
    agent_responses: dict  # {domain: response}
    
    # Output
    synthesized_response: str
    sources: List[str]
    dashboard_links: List[str]
    suggested_actions: List[str]
    
    # Memory context
    short_term_context: List[dict]
    user_preferences: dict
```

**Intent Classification Prompt Template:**
```
You are an intent classifier for [PROJECT_NAME].

Analyze the user query and classify it into ONE or MORE of these domains:
[LIST YOUR DOMAINS WITH DESCRIPTIONS]

Examples:
- "[Example query 1]" → ["domain_a"]
- "[Example query 2]" → ["domain_b", "domain_c"]
- "[Cross-domain query]" → ["domain_a", "domain_b"]

Return JSON: {"domains": ["domain1", "domain2"], "confidence": 0.95}

User Query: {query}
```

**Response Synthesis Prompt Template:**
```
You are synthesizing responses from specialized agents for [PROJECT_NAME].

User Question: {original_query}

Agent Responses:
{agent_responses}

Instructions:
1. Combine insights from all responding agents
2. Resolve any conflicts by preferring more specific data
3. Include relevant metrics and timeframes
4. Suggest dashboard links for deeper exploration
5. Recommend follow-up actions if appropriate

Provide a unified, conversational response.
```

### 2. Worker Agent (Genie-Based)

Each worker queries its dedicated Genie Space.

**Worker Configuration:**
```python
WORKER_CONFIGS = {
    "domain_a": {
        "genie_space_id": "your_genie_space_id_a",
        "description": "Handles [domain A] queries including [specific capabilities]",
        "example_queries": [
            "Example query 1",
            "Example query 2",
        ],
        "dashboard_id": "dashboard_id_for_domain_a"
    },
    "domain_b": {
        "genie_space_id": "your_genie_space_id_b",
        "description": "Handles [domain B] queries including [specific capabilities]",
        "example_queries": [
            "Example query 1",
            "Example query 2",
        ],
        "dashboard_id": "dashboard_id_for_domain_b"
    },
    # Add more domains...
}
```

**Genie Query Pattern:**
```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieAPI

class GenieWorkerAgent:
    def __init__(self, genie_space_id: str, domain_name: str):
        self.client = WorkspaceClient()
        self.genie = GenieAPI(self.client)
        self.space_id = genie_space_id
        self.domain = domain_name
    
    async def query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> dict:
        """Query Genie Space and return structured response."""
        
        # Enhance query with context
        enhanced_query = self._enhance_query(question, context)
        
        # Query Genie
        if conversation_id:
            response = self.genie.continue_conversation(
                space_id=self.space_id,
                conversation_id=conversation_id,
                content=enhanced_query
            )
        else:
            response = self.genie.start_conversation(
                space_id=self.space_id,
                content=enhanced_query
            )
        
        return {
            "response": response.result.content,
            "sources": response.result.sources or [],
            "domain": self.domain,
            "conversation_id": response.conversation_id
        }
```

### 3. Utility Tools

Beyond Genie, agents need these utility tools:

| Tool | Purpose | Implementation |
|------|---------|----------------|
| **Web Search** | Real-time information (status pages, docs) | Tavily API or similar |
| **Dashboard Linker** | Generate links to relevant dashboards | Workspace URL builder |
| **Alert Trigger** | Trigger alerts based on findings | Databricks SQL Alerts API |
| **Runbook RAG** | Look up operational procedures | Vector search on documentation |

**Tool Registration Pattern:**
```python
from langchain.tools import Tool

tools = [
    Tool(
        name="search_databricks_status",
        description="Check Databricks service status and known issues",
        func=search_databricks_status
    ),
    Tool(
        name="get_dashboard_link",
        description="Generate link to relevant AI/BI dashboard",
        func=generate_dashboard_link
    ),
    Tool(
        name="trigger_alert",
        description="Trigger an alert for critical findings",
        func=trigger_alert
    ),
    Tool(
        name="search_runbooks",
        description="Search operational runbooks for procedures",
        func=search_runbooks
    ),
]
```

---

## MLflow 3.0 Integration

### 1. Tracing Configuration

**Enable Automatic Tracing:**
```python
import mlflow
from mlflow.langchain import autolog

# At application startup
mlflow.set_experiment(f"/Shared/{project_name}_agents")
autolog(log_models=True, log_input_examples=True)
```

**Manual Span Instrumentation:**
```python
from mlflow.tracing import trace

@trace(name="orchestrator.classify_intent", span_type="LLM")
def classify_intent(query: str) -> dict:
    # Your classification logic
    pass

@trace(name="worker.query_genie", span_type="TOOL")
def query_genie_space(space_id: str, question: str) -> dict:
    # Your Genie query logic
    pass
```

### 2. Prompt Registry

**Register Prompts with Versioning:**
```python
from mlflow.genai import log_prompt

# Log orchestrator prompt
log_prompt(
    prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    artifact_path="prompts/orchestrator_system",
    registered_model_name=f"{project_name}_orchestrator_prompt"
)

# Log worker prompts
for domain, config in WORKER_CONFIGS.items():
    log_prompt(
        prompt=config["system_prompt"],
        artifact_path=f"prompts/{domain}_worker",
        registered_model_name=f"{project_name}_{domain}_prompt"
    )
```

**Load Production Prompts:**
```python
from mlflow.genai import load_prompt

orchestrator_prompt = load_prompt(
    f"prompts:/{project_name}_orchestrator_prompt/production"
)
```

### 3. Evaluation with LLM Judges

**Built-in Judges:**
```python
from mlflow.genai.scorers import (
    Relevance,
    Safety,
    Correctness,
    Groundedness
)

scorers = [
    Relevance(),      # Response relevance to query
    Safety(),         # Safety and appropriateness
    Correctness(),    # Factual accuracy
    Groundedness(),   # Grounded in provided context
]
```

**Custom Domain Judges:**
```python
from mlflow.genai import create_judge

# Create domain-specific judge
domain_accuracy_judge = create_judge(
    name=f"{domain}_accuracy",
    prompt="""
    Evaluate the {domain} response for accuracy:
    
    Query: {query}
    Response: {response}
    Expected Data Sources: {expected_sources}
    
    Criteria:
    1. Numbers and metrics are accurate
    2. Time periods are correctly interpreted  
    3. Domain terminology is used correctly
    4. Recommendations are actionable and appropriate
    
    Score: 0-1 (1 = fully accurate)
    Rationale: [Explain your scoring]
    """,
    output_schema={"score": float, "rationale": str}
)
```

**Run Evaluation:**
```python
from mlflow.genai import evaluate

results = evaluate(
    model=orchestrator_agent,
    data=benchmark_questions,  # DataFrame with query, expected_response columns
    scorers=scorers + [domain_accuracy_judge],
    evaluator_config={"temperature": 0.1}
)

# Log results
mlflow.log_metrics({
    "avg_relevance": results["relevance"].mean(),
    "avg_safety": results["safety"].mean(),
    "avg_domain_accuracy": results["domain_accuracy"].mean(),
})
```

### 4. Agent Logging and Registration

**ChatAgent Implementation:**
```python
from dataclasses import dataclass
from typing import Generator
import mlflow
from mlflow.pyfunc import ChatAgent
from mlflow.types.agent import (
    ChatAgentMessage,
    ChatAgentResponse,
    ChatAgentChunk
)

@dataclass
class AgentConfig:
    model_name: str = "databricks-meta-llama-3-1-70b-instruct"
    temperature: float = 0.7
    max_tokens: int = 4096

class OrchestratorAgent(ChatAgent):
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize LangGraph, workers, memory."""
        self.graph = self._build_langgraph()
        self.workers = self._initialize_workers()
        self.memory = self._initialize_memory()
    
    def predict(
        self,
        messages: list[ChatAgentMessage],
        context: Optional[dict] = None
    ) -> ChatAgentResponse:
        """Synchronous prediction."""
        # Extract query from messages
        query = messages[-1].content
        user_id = context.get("user_id") if context else None
        
        # Run orchestrator graph
        result = self.graph.invoke({
            "query": query,
            "user_id": user_id,
            "messages": messages
        })
        
        return ChatAgentResponse(
            messages=[ChatAgentMessage(
                role="assistant",
                content=result["synthesized_response"]
            )]
        )
    
    def predict_stream(
        self,
        messages: list[ChatAgentMessage],
        context: Optional[dict] = None
    ) -> Generator[ChatAgentChunk, None, None]:
        """Streaming prediction."""
        # Implementation for streaming responses
        pass
```

**Log and Register Agent:**
```python
with mlflow.start_run(run_name="orchestrator_v1"):
    # Log the agent
    mlflow.pyfunc.log_model(
        artifact_path="orchestrator",
        python_model=OrchestratorAgent(),
        registered_model_name=f"{project_name}_orchestrator",
        input_example={
            "messages": [{"role": "user", "content": "Example query"}]
        },
        pip_requirements=[
            "langchain>=0.1.0",
            "langgraph>=0.0.1",
            "databricks-sdk>=0.20.0",
            "mlflow>=2.12.0"
        ]
    )
    
    # Log metadata
    mlflow.log_params({
        "agent_type": "multi_agent_orchestrator",
        "num_workers": len(WORKER_CONFIGS),
        "domains": list(WORKER_CONFIGS.keys()),
    })
```

---

## Memory Management

### Short-Term Memory (Conversation Context)

```python
from databricks.agents.memory import LakebaseMemory

short_term = LakebaseMemory(
    table_name=f"{catalog}.{schema}.agent_short_term_memory",
    ttl_hours=24
)

# Save conversation turn
short_term.save(
    session_id=conversation_id,
    user_id=user_email,
    messages=[
        {"role": "user", "content": query},
        {"role": "assistant", "content": response}
    ]
)

# Retrieve recent context
history = short_term.retrieve(
    session_id=conversation_id,
    max_messages=10
)
```

### Long-Term Memory (User Preferences)

```python
long_term = LakebaseMemory(
    table_name=f"{catalog}.{schema}.agent_long_term_memory",
    ttl_days=365
)

# Save user preferences
long_term.save(
    user_id=user_email,
    insights={
        "preferred_domains": ["cost", "performance"],
        "default_time_range": "7d",
        "frequent_queries": ["cost by workspace", "failed jobs"],
        "alert_preferences": {"threshold": "high"}
    }
)

# Retrieve for personalization
preferences = long_term.retrieve(user_id=user_email)
```

---

## Deployment Configuration

### Model Serving Endpoint

```yaml
# resources/agents/orchestrator_serving.yml
resources:
  model_serving_endpoints:
    agent_orchestrator:
      name: ${var.project_name}_orchestrator
      config:
        served_entities:
          - name: orchestrator_v1
            entity_name: ${var.catalog}.${var.schema}.${var.project_name}_orchestrator
            entity_version: "1"
            workload_size: Small
            scale_to_zero_enabled: true
        auto_capture_config:
          catalog_name: ${var.catalog}
          schema_name: ${var.schema}
          table_name_prefix: agent_inference_
```

### Databricks App Frontend

```yaml
# resources/apps/agent_chat_app.yml
resources:
  apps:
    agent_chat:
      name: ${var.project_name}_chat
      description: "Chat interface for ${var.project_name} agents"
      source_code_path: ../src/apps/chat_ui
      resources:
        - name: serving_endpoint
          endpoint:
            name: ${var.project_name}_orchestrator
            permission: CAN_QUERY
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Define domains and worker configurations
- [ ] Set up MLflow experiment
- [ ] Create Genie Spaces for each domain (if not existing)
- [ ] Implement orchestrator state machine skeleton

### Phase 2: Core Agents (Week 2)
- [ ] Implement intent classification
- [ ] Create Genie worker agents for each domain
- [ ] Implement response synthesis
- [ ] Add MLflow tracing to all components

### Phase 3: Utility Tools (Week 3)
- [ ] Implement web search tool
- [ ] Implement dashboard linker
- [ ] Implement alert trigger
- [ ] Implement runbook RAG (if applicable)

### Phase 4: Memory & Personalization (Week 4)
- [ ] Set up Lakebase short-term memory
- [ ] Set up Lakebase long-term memory
- [ ] Integrate memory into orchestrator
- [ ] Add personalization logic

### Phase 5: Evaluation (Week 5)
- [ ] Create benchmark question set (100+ questions)
- [ ] Implement custom domain judges
- [ ] Run baseline evaluation
- [ ] Iterate on prompts based on results

### Phase 6: Logging & Registry (Week 6)
- [ ] Implement ChatAgent class
- [ ] Log agent to MLflow
- [ ] Register prompts in Prompt Registry
- [ ] Set up production aliases

### Phase 7: Deployment (Week 7)
- [ ] Deploy Model Serving endpoint
- [ ] Create Databricks App frontend
- [ ] Configure inference tables
- [ ] Set up monitoring dashboards

### Phase 8: Production Hardening (Week 8)
- [ ] Add error handling and fallbacks
- [ ] Implement rate limiting
- [ ] Add circuit breakers for external calls
- [ ] Create operational runbook

---

## Best Practices Summary

### DO ✅
- Use Genie as the SOLE interface for structured data
- Log all prompts to Prompt Registry with versions
- Instrument with MLflow tracing from day one
- Create domain-specific evaluation judges
- Use Lakebase for conversation memory
- Implement ChatAgent for proper model serving

### DON'T ❌
- Call TVFs/SQL directly from agents (use Genie)
- Hardcode prompts in agent code
- Skip tracing instrumentation
- Rely only on built-in judges for evaluation
- Store conversation state in memory only
- Deploy without proper logging/registry

---

## References

### Databricks Documentation
- [Multi-Agent with Genie](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)
- [Agent Framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
- [Log and Register Agents](https://docs.databricks.com/aws/en/generative-ai/agent-framework/log-agent)
- [Stateful Agents](https://docs.databricks.com/aws/en/generative-ai/agent-framework/stateful-agents)

### MLflow 3.0 Documentation
- [GenAI Concepts](https://docs.databricks.com/aws/en/mlflow3/genai/concepts/)
- [Tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/app-instrumentation/)
- [Evaluation & Scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)
- [Prompt Registry](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/)
- [Custom Judges](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-judge/create-custom-judge)

### Example Notebooks
- [LangGraph Multi-Agent Genie](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-multiagent-genie.html)
- [Short-Term Memory with Lakebase](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/short-term-memory-agent-lakebase.html)
- [Long-Term Memory with Lakebase](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/long-term-memory-agent-lakebase.html)

---

## Template Usage

To use this prompt for a new project:

1. **Copy this template** to your project's `context/prompts/` folder
2. **Fill in the Quick Start section** with your project specifics
3. **Customize WORKER_CONFIGS** with your domains and Genie Spaces
4. **Adapt the prompts** for your specific use case
5. **Follow the Implementation Checklist** phase by phase

This framework is designed to be adapted—not every project needs all components. Start with the core (orchestrator + Genie workers) and add complexity as needed.

---
name: lakebase-memory-patterns
description: Lakebase memory patterns for stateful agents - CheckpointSaver for short-term conversation continuity, DatabricksStore for long-term user preferences, graceful degradation, thread_id resolution
triggers:
  - memory
  - CheckpointSaver
  - DatabricksStore
  - Lakebase
  - stateful agent
  - conversation continuity
  - long-term memory
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
---

# Lakebase Memory Patterns for Stateful Agents

## When to Use

Use this skill when implementing stateful agents that need:
- **Short-term memory**: Conversation continuity within a session (thread_id)
- **Long-term memory**: User preferences and insights across sessions (user_id)
- **Graceful degradation**: Agent works without memory tables
- **Thread ID resolution**: Priority-based thread_id extraction from request context

## Two-Layer Memory Architecture

| Layer | Component | Use Case | Lifecycle |
|---|---|---|---|
| **Short-term** | CheckpointSaver | Conversation continuity within session | Thread-based, session-scoped |
| **Long-term** | DatabricksStore | User preferences across sessions | User-based, persistent |

## Core Principles

### 1. Unity Catalog-Backed Storage
- All memory stored in Unity Catalog Delta tables
- Governed, auditable, queryable
- Automatic schema management via `.setup()`
- TTL-based cleanup for GDPR compliance

### 2. Graceful Degradation
- Memory is optional enhancement, not requirement
- Agent works without memory tables
- Silent fallback if tables don't exist
- No failures due to missing memory

## Quick Setup

### Short-Term Memory

```python
from agents.memory import ShortTermMemory

# Initialize
memory = ShortTermMemory(instance_name="my_lakebase")

# Setup tables (run once)
memory.setup()

# Use with LangGraph
with memory.get_checkpointer() as checkpointer:
    graph = workflow.compile(checkpointer=checkpointer)
```

### Thread ID Resolution

```python
# Priority: custom_inputs > conversation_id > new UUID
thread_id = ShortTermMemory.resolve_thread_id(
    custom_inputs=request.custom_inputs,
    conversation_id=context.conversation_id
)

# Build LangGraph config
config = {"configurable": {"thread_id": thread_id}}
result = graph.invoke(messages, config=config)
```

### Long-Term Memory

```python
from agents.memory import LongTermMemory

# Initialize
memory = LongTermMemory(
    instance_name="my_lakebase",
    embedding_endpoint="databricks-gte-large-en",
    embedding_dims=1024
)

# Setup tables (run once)
memory.setup()

# Save user preference
memory.save_memory(
    user_id="user@example.com",
    memory_key="preferred_workspace",
    memory_data={"workspace_id": "12345"}
)

# Search memories
results = memory.search_memories(
    user_id="user@example.com",
    query="What workspace does the user prefer?",
    limit=5
)
```

## Common Mistakes to Avoid

### ❌ DON'T: Assume Tables Exist

```python
# BAD: Will fail if tables not created
class Agent:
    def __init__(self):
        self.memory = ShortTermMemory()
        with self.memory.get_checkpointer() as checkpointer:
            self.graph = workflow.compile(checkpointer=checkpointer)
```

### ✅ DO: Graceful Degradation

```python
# GOOD: Falls back gracefully
class Agent:
    def __init__(self):
        try:
            self.memory = ShortTermMemory()
            with self.memory.get_checkpointer() as checkpointer:
                self.graph = workflow.compile(checkpointer=checkpointer)
        except Exception as e:
            print(f"⚠ Memory unavailable, using stateless mode: {e}")
            self.graph = workflow.compile()  # No checkpointer
```

### ❌ DON'T: Forget to Return thread_id

```python
# BAD: Client can't track conversation
return {
    "choices": [{"message": {"content": response}}]
}
```

### ✅ DO: Return thread_id for Client Tracking

```python
# GOOD: Client can continue conversation
return {
    "choices": [{"message": {"content": response}}],
    "custom_outputs": {
        "thread_id": thread_id,  # ✅ Return for next turn
    }
}
```

### ❌ DON'T: Hardcode User IDs

```python
# BAD: Hardcoded user
memories = store.search_memories("hardcoded@example.com", query)
```

### ✅ DO: Extract from Context

```python
# GOOD: Dynamic user from request context
user_id = context.get("user_id") or custom_inputs.get("user_id") or "unknown"
memories = store.search_memories(user_id, query)
```

## Validation Checklist

Before deploying agent with memory:
- [ ] Lakebase instance name configured in settings
- [ ] Setup script run once (creates tables)
- [ ] Short-term memory uses `CheckpointSaver` with context manager
- [ ] Long-term memory uses `DatabricksStore` with embeddings
- [ ] Embedding endpoint configured (e.g., `databricks-gte-large-en`)
- [ ] Embedding dimensions match model (1024 for GTE-large)
- [ ] Thread ID resolution: custom_inputs → conversation_id → new UUID
- [ ] User ID extracted from context/custom_inputs
- [ ] Graceful degradation if tables don't exist
- [ ] thread_id returned in custom_outputs for client tracking
- [ ] Memory tools created with `create_memory_tools()` if autonomous use
- [ ] MLflow tracing enabled for memory operations

## References

### Detailed Patterns
- [Short-Term Memory](references/short-term-memory.md) - Complete CheckpointSaver implementation
- [Long-Term Memory](references/long-term-memory.md) - Complete DatabricksStore implementation
- [Graceful Degradation](references/graceful-degradation.md) - Fallback patterns

### Setup Scripts
- [Setup Lakebase](scripts/setup_lakebase.py) - Table initialization script

### Official Documentation
- [Databricks Short-Term Memory Pattern](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/short-term-memory-agent-lakebase.html)
- [Databricks Long-Term Memory Pattern](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/long-term-memory-agent-lakebase.html)
- [Stateful Agents Guide](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/stateful-agents)
- [Lakebase Documentation](https://docs.databricks.com/en/lakebase/)

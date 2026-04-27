# Short-Term Memory with CheckpointSaver

Complete implementation of short-term memory using Lakebase CheckpointSaver for conversation continuity within a session.

## ShortTermMemory Class

**File: `src/agents/memory/short_term.py`**

```python
"""
Short-Term Memory with Lakebase CheckpointSaver
==============================================

Implements conversation-level state persistence using Databricks Lakebase.

Reference:
    https://docs.databricks.com/aws/en/notebooks/source/generative-ai/short-term-memory-agent-lakebase.html
"""

from typing import Optional, Generator
from contextlib import contextmanager
import uuid
import mlflow

from databricks_langchain import CheckpointSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from ..config import settings


class ShortTermMemory:
    """
    Short-term memory manager using Lakebase CheckpointSaver.
    
    Provides thread ID management for conversation continuity.
    """
    
    def __init__(self, instance_name: Optional[str] = None):
        """
        Initialize short-term memory.
        
        Args:
            instance_name: Lakebase instance name. Defaults to settings value.
        """
        self.instance_name = instance_name or settings.lakebase_instance_name
        self._checkpointer: Optional[CheckpointSaver] = None
    
    def setup(self) -> None:
        """
        Initialize Lakebase checkpoint tables.
        
        Creates necessary tables for storing LangGraph checkpoints.
        Should be called once during initial setup.
        """
        with mlflow.start_span(name="setup_checkpoint_tables", span_type="MEMORY") as span:
            span.set_inputs({"instance_name": self.instance_name})
            
            with CheckpointSaver(instance_name=self.instance_name) as saver:
                saver.setup()
            
            span.set_outputs({"status": "success"})
    
    @contextmanager
    def get_checkpointer(self) -> Generator[BaseCheckpointSaver, None, None]:
        """
        Get a checkpoint saver context for LangGraph compilation.
        
        Yields:
            CheckpointSaver instance for use with LangGraph.
        
        Example:
            with memory.get_checkpointer() as checkpointer:
                graph = workflow.compile(checkpointer=checkpointer)
        """
        with CheckpointSaver(instance_name=self.instance_name) as checkpointer:
            yield checkpointer
    
    @staticmethod
    def generate_thread_id() -> str:
        """Generate a new unique thread ID for a conversation."""
        return str(uuid.uuid4())
    
    @staticmethod
    @mlflow.trace(name="resolve_thread_id", span_type="MEMORY")
    def resolve_thread_id(
        custom_inputs: Optional[dict] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Resolve thread ID from various sources.
        
        Priority:
            1. custom_inputs["thread_id"] - Explicit thread ID
            2. conversation_id - From ChatContext
            3. New UUID - Fresh conversation
        
        Args:
            custom_inputs: Custom inputs dict from request
            conversation_id: Conversation ID from ChatContext
        
        Returns:
            Thread ID string for checkpoint configuration.
        """
        # Check custom_inputs first
        if custom_inputs and custom_inputs.get("thread_id"):
            return custom_inputs["thread_id"]
        
        # Fall back to conversation_id
        if conversation_id:
            return conversation_id
        
        # Generate new thread ID
        return ShortTermMemory.generate_thread_id()
    
    @staticmethod
    def get_checkpoint_config(thread_id: str) -> dict:
        """
        Build LangGraph checkpoint configuration.
        
        Args:
            thread_id: Thread ID for the conversation
        
        Returns:
            Configuration dict for LangGraph invocation.
        """
        return {"configurable": {"thread_id": thread_id}}


# Module-level convenience function
@contextmanager
def get_checkpoint_saver(
    instance_name: Optional[str] = None
) -> Generator[BaseCheckpointSaver, None, None]:
    """
    Get a CheckpointSaver for LangGraph state persistence.
    
    This is the recommended way to use short-term memory with LangGraph.
    
    Example:
        from agents.memory import get_checkpoint_saver
        
        with get_checkpoint_saver() as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            
            thread_id = request.custom_inputs.get("thread_id") or str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            
            result = graph.invoke({"messages": messages}, config)
    """
    memory = ShortTermMemory(instance_name)
    with memory.get_checkpointer() as checkpointer:
        yield checkpointer
```

## Integration with LangGraph Agent

```python
from agents.memory import get_checkpoint_saver, ShortTermMemory
from langgraph.graph import StateGraph

class HealthMonitorAgent(mlflow.pyfunc.ResponsesAgent):
    """Agent with short-term memory."""
    
    def __init__(self):
        super().__init__()
        self._short_term_memory = None
        self._short_term_memory_available = True
    
    def _get_short_term_memory(self):
        """Lazy-load short-term memory."""
        if self._short_term_memory is None:
            self._short_term_memory = ShortTermMemory()
        return self._short_term_memory
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with checkpointing."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("orchestrator", self._orchestrator_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        # Add edges
        workflow.set_entry_point("orchestrator")
        workflow.add_edge("orchestrator", "synthesizer")
        workflow.set_finish_point("synthesizer")
        
        # ✅ CRITICAL: Compile with checkpointer
        try:
            memory = self._get_short_term_memory()
            with memory.get_checkpointer() as checkpointer:
                graph = workflow.compile(checkpointer=checkpointer)
                self._short_term_memory_available = True
                return graph
        except Exception as e:
            print(f"⚠ Short-term memory unavailable: {e}")
            # Graceful fallback: compile without checkpointer
            self._short_term_memory_available = False
            return workflow.compile()
    
    def predict(self, context, model_input, params=None):
        """Execute agent with conversation continuity."""
        # Extract thread_id for conversation continuity
        custom_inputs = model_input.get("custom_inputs", {})
        conversation_id = context.get("conversation_id")
        
        # Resolve thread ID (priority: custom_inputs > conversation_id > new)
        thread_id = ShortTermMemory.resolve_thread_id(
            custom_inputs=custom_inputs,
            conversation_id=conversation_id
        )
        
        # Build LangGraph config with thread_id
        if self._short_term_memory_available:
            config = {"configurable": {"thread_id": thread_id}}
        else:
            config = {}
        
        # Execute graph with checkpoint persistence
        graph = self._build_graph()
        result = graph.invoke(
            {"messages": model_input["messages"]},
            config=config
        )
        
        # Return response with thread_id for client to track
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": result["messages"][-1].content
                }
            }],
            "custom_outputs": {
                "thread_id": thread_id,  # ✅ Return for client tracking
            }
        }
```

## Thread ID Resolution Priority

The `resolve_thread_id` method follows this priority order:

1. **custom_inputs["thread_id"]** - Explicit thread ID from client request
2. **conversation_id** - Conversation ID from ChatContext
3. **New UUID** - Generate fresh thread ID for new conversation

This ensures:
- Client can explicitly control conversation continuity
- Existing conversations continue seamlessly
- New conversations get unique thread IDs

## Checkpoint Configuration Pattern

Always use the `get_checkpoint_config` helper to build LangGraph configuration:

```python
thread_id = ShortTermMemory.resolve_thread_id(...)
config = ShortTermMemory.get_checkpoint_config(thread_id)
# Returns: {"configurable": {"thread_id": "..."}}

result = graph.invoke(messages, config=config)
```

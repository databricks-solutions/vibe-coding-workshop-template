# Graceful Degradation Pattern

**CRITICAL: Memory is optional - agent must work without it.**

Complete graceful degradation implementation ensuring agents function correctly even when memory tables don't exist.

## Graceful Degradation Pattern

**CRITICAL: Memory is optional - agent must work without it.**

```python
class HealthMonitorAgent(mlflow.pyfunc.ResponsesAgent):
    """Agent with optional memory support."""
    
    def __init__(self):
        super().__init__()
        self._short_term_memory = None
        self._long_term_memory = None
        
        # Track availability (set to False if setup fails)
        self._short_term_memory_available = True
        self._long_term_memory_available = True
    
    def _get_short_term_memory(self):
        """Lazy-load short-term memory with error handling."""
        if self._short_term_memory is None and self._short_term_memory_available:
            try:
                self._short_term_memory = ShortTermMemory()
                # Test if tables exist by attempting to get checkpointer
                with self._short_term_memory.get_checkpointer():
                    pass
            except Exception as e:
                print(f"⚠ Short-term memory unavailable: {e}")
                self._short_term_memory_available = False
                self._short_term_memory = None
        
        return self._short_term_memory
    
    def _get_long_term_memory(self):
        """Lazy-load long-term memory with error handling."""
        if self._long_term_memory is None and self._long_term_memory_available:
            try:
                self._long_term_memory = LongTermMemory()
                # Test if tables exist by attempting a search
                self._long_term_memory.search_memories("test", "test", limit=1)
            except Exception as e:
                print(f"⚠ Long-term memory unavailable: {e}")
                self._long_term_memory_available = False
                self._long_term_memory = None
        
        return self._long_term_memory
    
    def predict(self, context, model_input, params=None):
        """Execute agent with optional memory."""
        # Try to use short-term memory, fall back to stateless
        if self._short_term_memory_available:
            memory = self._get_short_term_memory()
            if memory:
                # Build with checkpointer
                with memory.get_checkpointer() as checkpointer:
                    graph = self._workflow.compile(checkpointer=checkpointer)
            else:
                # Compile without checkpointer
                graph = self._workflow.compile()
        else:
            # Compile without checkpointer
            graph = self._workflow.compile()
        
        # Execute normally
        result = graph.invoke({"messages": model_input["messages"]})
        
        return self._format_response(result)
```

---



## Key Patterns

### 1. Availability Flags

Track memory availability with boolean flags:

```python
self._short_term_memory_available = True
self._long_term_memory_available = True
```

Set to `False` on first failure to prevent repeated attempts.

### 2. Lazy Loading with Testing

Test memory availability before using:

```python
try:
    memory = ShortTermMemory()
    # Test if tables exist
    with memory.get_checkpointer():
        pass
    self._short_term_memory_available = True
except Exception as e:
    print(f"⚠ Memory unavailable: {e}")
    self._short_term_memory_available = False
```

### 3. Silent Fallback

Never raise exceptions - always fall back gracefully:

```python
if self._short_term_memory_available:
    # Try to use memory
    try:
        # Use memory
    except Exception:
        # Fall back to stateless
        pass
else:
    # Use stateless mode
    pass
```

### 4. User ID Extraction with Fallback

Always provide fallback for user ID:

```python
user_id = (
    context.get("user_id") or 
    custom_inputs.get("user_id") or 
    "unknown"
)
```

### 5. Thread ID Resolution with Fallback

Thread ID resolution always succeeds (generates new if needed):

```python
thread_id = ShortTermMemory.resolve_thread_id(
    custom_inputs=custom_inputs,
    conversation_id=conversation_id
)
# Always returns a valid thread_id
```

## Error Handling Best Practices

### ✅ DO: Catch and Log

```python
try:
    memories = memory.search_memories(user_id, query)
except Exception as e:
    print(f"⚠ Memory search failed: {e}")
    memories = []  # Empty result, continue execution
```

### ❌ DON'T: Let Exceptions Propagate

```python
# BAD: Will crash agent if memory unavailable
memories = memory.search_memories(user_id, query)  # ❌ Raises exception
```

### ✅ DO: Check Availability First

```python
# GOOD: Check flag before using
if self._long_term_memory_available:
    memories = memory.search_memories(user_id, query)
else:
    memories = []  # Graceful fallback
```

## Testing Memory Availability

### Test Short-Term Memory

```python
def test_short_term_memory():
    """Test if short-term memory tables exist."""
    try:
        memory = ShortTermMemory()
        with memory.get_checkpointer():
            pass
        return True
    except Exception:
        return False
```

### Test Long-Term Memory

```python
def test_long_term_memory():
    """Test if long-term memory tables exist."""
    try:
        memory = LongTermMemory()
        # Attempt a test search
        memory.search_memories("test", "test", limit=1)
        return True
    except Exception:
        return False
```

## Deployment Checklist

Before deploying agent with memory:
- [ ] Memory setup script run successfully
- [ ] Tables verified in Unity Catalog
- [ ] Graceful degradation tested (disable tables, verify agent still works)
- [ ] Error logging configured for memory failures
- [ ] Fallback behavior documented
- [ ] User ID extraction tested with various contexts
- [ ] Thread ID resolution tested (new and existing conversations)

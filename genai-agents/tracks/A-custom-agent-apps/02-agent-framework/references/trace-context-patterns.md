# Trace Context Patterns

## Tags vs Metadata

**Reference:** [Attach Custom Tags and Metadata](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/tracing/attach-tags/)

| Property | Mutability | Use For | Example |
|---|---|---|---|
| **Metadata** | Immutable (write-once) | Fixed information captured during execution | User ID, session ID, model version, environment |
| **Tags** | Mutable (can update) | Dynamic information that may change | User feedback, review status, quality assessments |

---

## Standard Metadata Fields

**Reference:** [Add Context to Traces](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/tracing/add-context-to-traces)

MLflow provides standardized metadata fields that enable automatic filtering and grouping in the UI:

```python
import mlflow

mlflow.update_current_trace(
    metadata={
        # ========== USER & SESSION TRACKING ==========
        "mlflow.trace.user": user_id,           # Associate with specific user
        "mlflow.trace.session": session_id,     # Group multi-turn conversations
        
        # ========== DEPLOYMENT CONTEXT ==========
        "mlflow.source.type": "PRODUCTION",     # Environment (PRODUCTION, STAGING, DEV)
        "mlflow.source.name": "health-monitor-agent",  # Application name
        "mlflow.modelId": "v2.1.0",             # Application version
        
        # ========== GIT CONTEXT (auto-populated if in repo) ==========
        "mlflow.source.git.commit": commit_hash,   # Git commit hash
        "mlflow.source.git.branch": branch_name,   # Git branch
        "mlflow.source.git.repoURL": repo_url,     # Git repository URL
        
        # ========== REQUEST TRACKING ==========
        "client_request_id": request_id,        # Link to client request
        
        # ========== CUSTOM METADATA ==========
        "deployment_region": "us-west-2",       # Custom metadata
        "feature_flags": "new_routing,caching", # Application-specific
    }
)
```

## Standard Tagging Pattern (Mutable Context)

```python
mlflow.update_current_trace(
    tags={
        # ========== QUERY CLASSIFICATION ==========
        "query_category": "cost_analysis",
        "domains": "cost,reliability",
        "confidence": "0.95",
        
        # ========== EXECUTION DETAILS ==========
        "streaming": "true",
        "genie_used": "true",
        "cache_hit": "false",
        
        # ========== QUALITY ASSESSMENT ==========
        "review_status": "approved",
        "data_quality": "high",
        
        # ========== BUSINESS CONTEXT ==========
        "customer_tier": "enterprise",
        "use_case": "cost_optimization",
    }
)
```

---

## Complete Production Context Pattern

Full pattern showing how to set trace context during `predict()`:

```python
@mlflow.trace(name="health_monitor_predict", span_type="AGENT")
def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    """Predict with comprehensive trace context."""
    
    # ========== EXTRACT CONTEXT FROM REQUEST ==========
    
    input_messages = [msg.model_dump() for msg in request.input]
    query = input_messages[-1].get("content", "")
    custom_inputs = request.custom_inputs or {}
    
    # User context
    user_id = custom_inputs.get("user_id", "unknown")
    session_id = custom_inputs.get("session_id", str(uuid.uuid4()))
    thread_id = custom_inputs.get("thread_id", str(uuid.uuid4()))
    
    # Request context
    client_request_id = custom_inputs.get("request_id", str(uuid.uuid4()))
    
    # Deployment context
    app_environment = os.environ.get("APP_ENVIRONMENT", "development")
    app_version = os.environ.get("APP_VERSION", "dev")
    deployment_region = os.environ.get("DEPLOYMENT_REGION", "unknown")
    endpoint_name = os.environ.get("ENDPOINT_NAME", "health-monitor-agent")
    
    # ========== UPDATE TRACE WITH METADATA (Immutable) ==========
    
    mlflow.update_current_trace(
        metadata={
            # User & Session (standard fields for UI filtering)
            "mlflow.trace.user": user_id,
            "mlflow.trace.session": session_id,
            
            # Deployment context
            "mlflow.source.type": app_environment.upper(),  # PRODUCTION, STAGING, DEV
            "mlflow.modelId": app_version,
            "client_request_id": client_request_id,
            
            # Custom application metadata
            "deployment_region": deployment_region,
            "endpoint_name": endpoint_name,
            "query_length": str(len(query)),
            "has_custom_inputs": str(bool(custom_inputs)),
        },
        tags={
            # Execution details (mutable - can update later)
            "user_id": user_id,         # Also in metadata, but tags are filterable
            "thread_id": thread_id,     # For conversation tracking
            "session_id": session_id,   # For multi-turn analysis
            "query_length": str(len(query)),
            "streaming": "pending",     # Can update to "true" later
        }
    )
    
    # ========== PROCESS QUERY ==========
    
    response_text, domains = self._process(query, custom_inputs)
    
    # ========== UPDATE TRACE WITH EXECUTION RESULTS (Tags) ==========
    
    mlflow.update_current_trace(tags={
        "domains_queried": ",".join(domains),
        "streaming": "false",  # Updated from "pending"
        "response_generated": "true",
    })
    
    # Return response
    return ResponsesAgentResponse(
        output=[self.create_text_output_item(text=response_text, id=str(uuid.uuid4()))],
        custom_outputs={
            "thread_id": thread_id,         # Return for client tracking
            "session_id": session_id,
            "domains_queried": domains,
        }
    )
```

---

## Safe Trace Update Helper

**Problem:** `mlflow.update_current_trace()` raises warnings during evaluation when no active trace exists.

**Solution:** Check for active trace before updating.

```python
def _safe_update_trace(metadata: dict = None, tags: dict = None) -> bool:
    """
    Safely update the current MLflow trace without triggering warnings.
    
    During evaluation testing, there may not be an active trace context.
    This helper checks for an active trace before attempting updates.
    
    Returns:
        True if update succeeded, False if no active trace.
    """
    try:
        # Check if there's an active trace
        current_span = mlflow.get_current_active_span()
        if current_span is None:
            return False
        
        # Safe to update
        mlflow.update_current_trace(metadata=metadata, tags=tags)
        return True
    except Exception:
        return False


# Usage in agent
_safe_update_trace(
    metadata={"mlflow.trace.user": user_id},
    tags={"query_category": "cost"}
)
```

---

## Updating Tags on Finished Traces

**After a trace is logged, only tags can be updated (not metadata).**

**Reference:** [Setting Tags on Finished Traces](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/tracing/attach-tags/#setting-tags-on-a-finished-trace)

```python
import mlflow

# Execute traced function
@mlflow.trace
def process_query(query):
    return f"Processed: {query}"

result = process_query("Why did costs spike?")

# ========== GET TRACE ID ==========
trace_id = mlflow.get_last_active_trace_id()

# ========== SET/UPDATE TAGS ON FINISHED TRACE ==========

# Add review status after human review
mlflow.set_trace_tag(
    trace_id=trace_id,
    key="review_status",
    value="approved"
)

# Add quality assessment after evaluation
mlflow.set_trace_tag(
    trace_id=trace_id,
    key="quality_score",
    value="0.85"
)

# ========== DELETE TAG ==========

mlflow.delete_trace_tag(
    trace_id=trace_id,
    key="quality_score"  # Remove tag
)
```

---

## Multi-Turn Conversation Tracking

```python
class ConversationAgent(ResponsesAgent):
    """Agent with session and conversation tracking."""
    
    @mlflow.trace(name="predict", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Predict with conversation context."""
        
        # Extract conversation identifiers
        custom_inputs = request.custom_inputs or {}
        user_id = custom_inputs.get("user_id", "anonymous")
        session_id = custom_inputs.get("session_id")
        thread_id = custom_inputs.get("thread_id")
        
        # Generate IDs if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        # CRITICAL: Use standard metadata fields for UI filtering
        mlflow.update_current_trace(
            metadata={
                "mlflow.trace.user": user_id,       # Standard user field
                "mlflow.trace.session": session_id, # Standard session field
                "turn_number": str(custom_inputs.get("turn_number", 1)),
            },
            tags={
                "thread_id": thread_id,
                "conversation_type": "multi_turn",
                "user_tier": custom_inputs.get("user_tier", "standard"),
            }
        )
        
        # Load conversation history using thread_id
        history = self._get_conversation_history(thread_id)
        
        # Process with context
        response = self._process_with_history(query, history)
        
        # Return with IDs for client tracking
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=response, id=str(uuid.uuid4()))],
            custom_outputs={
                "session_id": session_id,
                "thread_id": thread_id,
                "turn_number": len(history) + 1,
            }
        )
```

---

## Environment-Specific Context

```python
import os

def add_deployment_context():
    """Add deployment environment context to trace."""
    
    # Extract from environment variables (not hardcoded)
    mlflow.update_current_trace(
        metadata={
            # Override automatic detection
            "mlflow.source.type": os.getenv("APP_ENVIRONMENT", "DEVELOPMENT"),
            "mlflow.source.name": os.getenv("APP_NAME", "health-monitor-agent"),
            "mlflow.modelId": os.getenv("APP_VERSION", "dev"),
            
            # Custom deployment metadata
            "deployment_id": os.getenv("DEPLOYMENT_ID", "unknown"),
            "deployment_region": os.getenv("AWS_REGION", "us-west-2"),
            "k8s_pod_name": os.getenv("HOSTNAME", "unknown"),
        },
        tags={
            # Feature flags (can change without redeployment)
            "feature_new_routing": os.getenv("FEATURE_NEW_ROUTING", "false"),
            "feature_caching": os.getenv("FEATURE_CACHING", "true"),
        }
    )
```

---

## Query Patterns for Trace Context

```python
import mlflow

# ========== SEARCH TRACES BY USER ==========

user_traces = mlflow.search_traces(
    filter_string="metadata.mlflow.trace.user = 'user@example.com'",
    max_results=100
)

# ========== SEARCH TRACES BY SESSION ==========

session_traces = mlflow.search_traces(
    filter_string="metadata.mlflow.trace.session = 'session_123'",
    order_by=["timestamp ASC"]  # Chronological order
)

# ========== SEARCH TRACES BY ENVIRONMENT ==========

prod_traces = mlflow.search_traces(
    filter_string="metadata.mlflow.source.type = 'PRODUCTION'",
    max_results=1000
)

# ========== SEARCH BY TAG ==========

reviewed_traces = mlflow.search_traces(
    filter_string="tags.review_status = 'approved'",
    max_results=50
)

# ========== COMPLEX FILTER ==========

filtered_traces = mlflow.search_traces(
    filter_string="""
        metadata.mlflow.trace.user = 'user@example.com'
        AND tags.domains LIKE '%cost%'
        AND metadata.mlflow.source.type = 'PRODUCTION'
    """,
    max_results=100
)
```

---

## Span Types Reference

| Type | Use For | Example |
|---|---|---|
| `AGENT` | Top-level agent | `predict()` |
| `CHAIN` | Multi-step pipeline | LangGraph workflow |
| `TOOL` | Tool invocations | Genie query, web search |
| `LLM` | Direct LLM calls | Intent classification |
| `CLASSIFIER` | Classification operations | Intent classification |
| `RETRIEVER` | Data retrieval | Memory search, RAG |
| `MEMORY` | Memory operations | Save/load memory |
| `JUDGE` | Evaluation scoring | Custom scorers |
| `PARSER` | Output parsing | JSON extraction |

---

## References

- [Add Context to Traces](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/tracing/add-context-to-traces) - Primary reference for metadata/tags
- [Attach Custom Tags and Metadata](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/tracing/attach-tags/) - Tags vs metadata
- [Standard Metadata Fields](https://mlflow.org/docs/latest/genai/tracing/track-environments-context/#reserved-standard-tags) - MLflow conventions
- [Search Traces Programmatically](https://mlflow.org/docs/latest/genai/tracing/search-traces/) - Query patterns

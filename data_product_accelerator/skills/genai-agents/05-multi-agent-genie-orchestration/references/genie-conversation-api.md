# Genie Conversation API Patterns

Complete patterns for querying Databricks Genie Spaces via the Conversation API, including conversation management, query result extraction, and error handling.

## Complete Query Flow

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.genie import (
    StartConversationRequest,
    ContinueConversationRequest,
    GetConversationRequest,
    GetMessageRequest,
)
from typing import Optional, Dict, Any
import time

def start_conversation_and_wait(
    workspace_client: WorkspaceClient,
    space_id: str,
    query: str,
    conversation_id: Optional[str] = None,
    max_wait_seconds: int = 60,
    poll_interval_seconds: int = 2
) -> Dict[str, Any]:
    """
    Start or continue a Genie conversation and wait for completion.
    
    Args:
        workspace_client: Authenticated WorkspaceClient
        space_id: Genie Space ID
        query: User query string
        conversation_id: Optional conversation ID for follow-up queries
        max_wait_seconds: Maximum time to wait for response
        poll_interval_seconds: Polling interval for checking completion
    
    Returns:
        {
            "conversation_id": str,
            "message_id": str,
            "query_result": dict,  # From attachment
            "response_text": str,
            "success": bool
        }
    """
    try:
        if conversation_id:
            # Continue existing conversation
            response = workspace_client.genie.continue_conversation(
                conversation_id=conversation_id,
                request=ContinueConversationRequest(message=query)
            )
        else:
            # Start new conversation
            response = workspace_client.genie.start_conversation(
                space_id=space_id,
                request=StartConversationRequest(message=query)
            )
            conversation_id = response.conversation_id
        
        message_id = response.message_id
        
        # Wait for message completion
        message = _wait_for_message_completion(
            workspace_client,
            conversation_id,
            message_id,
            max_wait_seconds,
            poll_interval_seconds
        )
        
        # Extract query result from attachment
        query_result = get_message_attachment_query_result(
            workspace_client,
            conversation_id,
            message_id
        )
        
        return {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "query_result": query_result,
            "response_text": message.response_text or "",
            "success": True
        }
        
    except Exception as e:
        return {
            "conversation_id": conversation_id if 'conversation_id' in locals() else None,
            "message_id": message_id if 'message_id' in locals() else None,
            "query_result": None,
            "response_text": "",
            "success": False,
            "error": str(e)
        }


def _wait_for_message_completion(
    workspace_client: WorkspaceClient,
    conversation_id: str,
    message_id: str,
    max_wait_seconds: int,
    poll_interval_seconds: int
):
    """Wait for message to complete, polling until done or timeout."""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        message = workspace_client.genie.get_message(
            conversation_id=conversation_id,
            message_id=message_id
        )
        
        # Check if message is complete
        if message.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return message
        
        time.sleep(poll_interval_seconds)
    
    raise TimeoutError(
        f"Message {message_id} did not complete within {max_wait_seconds} seconds"
    )


def get_message_attachment_query_result(
    workspace_client: WorkspaceClient,
    conversation_id: str,
    message_id: str
) -> Optional[Dict[str, Any]]:
    """
    Extract query result from message attachment.
    
    Returns the SQL query result if available, None otherwise.
    """
    try:
        message = workspace_client.genie.get_message(
            conversation_id=conversation_id,
            message_id=message_id
        )
        
        # Check for query result attachment
        if not message.attachments:
            return None
        
        for attachment in message.attachments:
            if attachment.type == "QUERY_RESULT":
                # Query result attachment contains the SQL execution result
                return {
                    "sql_query": attachment.query_result.sql_query if hasattr(attachment.query_result, 'sql_query') else None,
                    "result_data": attachment.query_result.result_data if hasattr(attachment.query_result, 'result_data') else None,
                    "columns": attachment.query_result.columns if hasattr(attachment.query_result, 'columns') else None,
                    "row_count": attachment.query_result.row_count if hasattr(attachment.query_result, 'row_count') else None,
                }
        
        return None
        
    except Exception as e:
        # Attachment extraction failed - return None
        return None


def _format_query_results(
    query_result: Optional[Dict[str, Any]],
    format_type: str = "markdown"
) -> str:
    """
    Format query result for display.
    
    Args:
        query_result: Query result dict from get_message_attachment_query_result()
        format_type: "markdown" or "text"
    
    Returns:
        Formatted string representation
    """
    if not query_result:
        return "No query result available."
    
    if format_type == "markdown":
        # Format as markdown table
        if query_result.get("columns") and query_result.get("result_data"):
            columns = query_result["columns"]
            rows = query_result["result_data"]
            
            # Build markdown table
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"
            body_rows = [
                "| " + " | ".join(str(cell) for cell in row) + " |"
                for row in rows
            ]
            
            return "\n".join([header, separator] + body_rows)
        else:
            return f"Query executed: {query_result.get('sql_query', 'N/A')}"
    
    else:
        # Plain text format
        if query_result.get("result_data"):
            return str(query_result["result_data"])
        else:
            return f"Query: {query_result.get('sql_query', 'N/A')}"


def query_genie(
    workspace_client: WorkspaceClient,
    space_id: str,
    query: str,
    conversation_id: Optional[str] = None,
    include_query_result: bool = True
) -> Dict[str, Any]:
    """
    Complete Genie query function with error handling.
    
    Args:
        workspace_client: Authenticated WorkspaceClient
        space_id: Genie Space ID
        query: User query
        conversation_id: Optional conversation ID for follow-ups
        include_query_result: Whether to extract query result attachment
    
    Returns:
        {
            "conversation_id": str,
            "message_id": str,
            "response_text": str,
            "query_result": dict | None,
            "formatted_result": str,
            "success": bool
        }
    """
    result = start_conversation_and_wait(
        workspace_client=workspace_client,
        space_id=space_id,
        query=query,
        conversation_id=conversation_id
    )
    
    if not result["success"]:
        return result
    
    # Format query result if available
    formatted_result = None
    if include_query_result and result["query_result"]:
        formatted_result = _format_query_results(
            result["query_result"],
            format_type="markdown"
        )
    
    return {
        "conversation_id": result["conversation_id"],
        "message_id": result["message_id"],
        "response_text": result["response_text"],
        "query_result": result["query_result"],
        "formatted_result": formatted_result,
        "success": True
    }
```

## Conversation ID Tracking for Follow-ups

```python
class GenieConversationManager:
    """Manages conversation state for multi-turn Genie queries."""
    
    def __init__(self, workspace_client: WorkspaceClient):
        self.workspace_client = workspace_client
        self.conversations: Dict[str, str] = {}  # domain -> conversation_id
    
    def query_domain(
        self,
        domain: str,
        space_id: str,
        query: str,
        use_follow_up: bool = True
    ) -> Dict[str, Any]:
        """
        Query a domain, optionally continuing existing conversation.
        
        Args:
            domain: Domain name (e.g., "billing", "monitoring")
            space_id: Genie Space ID
            query: User query
            use_follow_up: Whether to continue existing conversation
        
        Returns:
            Query result dict
        """
        conversation_id = None
        if use_follow_up and domain in self.conversations:
            conversation_id = self.conversations[domain]
        
        result = query_genie(
            workspace_client=self.workspace_client,
            space_id=space_id,
            query=query,
            conversation_id=conversation_id
        )
        
        # Update conversation ID for next query
        if result["success"] and result["conversation_id"]:
            self.conversations[domain] = result["conversation_id"]
        
        return result
    
    def reset_conversation(self, domain: str):
        """Reset conversation for a domain."""
        if domain in self.conversations:
            del self.conversations[domain]
```

## Error Handling Patterns

```python
class GenieQueryError(Exception):
    """Base exception for Genie query errors."""
    pass

class GenieTimeoutError(GenieQueryError):
    """Genie query timed out."""
    pass

class GenieSpaceNotFoundError(GenieQueryError):
    """Genie Space not found."""
    pass

def query_genie_with_error_handling(
    workspace_client: WorkspaceClient,
    space_id: str,
    query: str
) -> Dict[str, Any]:
    """
    Query Genie with comprehensive error handling.
    
    Raises:
        GenieSpaceNotFoundError: If space doesn't exist
        GenieTimeoutError: If query times out
        GenieQueryError: For other Genie errors
    """
    try:
        # Verify space exists
        try:
            space = workspace_client.genie.get_space(space_id=space_id)
        except Exception as e:
            raise GenieSpaceNotFoundError(
                f"Genie Space {space_id} not found: {str(e)}"
            )
        
        # Execute query
        result = query_genie(
            workspace_client=workspace_client,
            space_id=space_id,
            query=query
        )
        
        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            if "timeout" in error_msg.lower():
                raise GenieTimeoutError(f"Query timed out: {error_msg}")
            else:
                raise GenieQueryError(f"Query failed: {error_msg}")
        
        return result
        
    except (GenieSpaceNotFoundError, GenieTimeoutError, GenieQueryError):
        raise
    except Exception as e:
        raise GenieQueryError(f"Unexpected error: {str(e)}")
```

## Usage Example

```python
from databricks.sdk import WorkspaceClient

# Initialize workspace client
workspace_client = WorkspaceClient()

# Query a Genie Space
result = query_genie(
    workspace_client=workspace_client,
    space_id="1234567890abcdef",
    query="What was the total cost last month?"
)

if result["success"]:
    print(f"Response: {result['response_text']}")
    if result["formatted_result"]:
        print(f"\nQuery Result:\n{result['formatted_result']}")
else:
    print(f"Error: {result.get('error', 'Unknown error')}")

# Follow-up query in same conversation
follow_up_result = query_genie(
    workspace_client=workspace_client,
    space_id="1234567890abcdef",
    query="What about this month?",
    conversation_id=result["conversation_id"]
)
```

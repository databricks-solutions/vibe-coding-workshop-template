"""
Production Agent Template - ResponsesAgent
==========================================

Template for creating a Databricks GenAI agent using MLflow ResponsesAgent.
Replace placeholder values with your domain-specific configuration.

MANDATORY: This class must inherit from ResponsesAgent for AI Playground compatibility.
"""

import os
import uuid
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    ResponsesAgentStreamEventDelta,
    ResponsesAgentMessageContentDelta,
)
from typing import Generator, Optional


class YourDomainAgent(ResponsesAgent):
    """
    Production agent using ResponsesAgent pattern.
    
    CRITICAL:
    - Must inherit from ResponsesAgent (NOT ChatAgent, NOT PythonModel)
    - predict() must return ResponsesAgentResponse
    - NO manual signature parameter in log_model()
    """
    
    # Domain keyword mapping for intent classification
    DOMAIN_KEYWORDS = {
        "domain1": ["keyword1", "keyword2", "keyword3"],
        "domain2": ["keyword4", "keyword5", "keyword6"],
    }
    
    def __init__(self):
        super().__init__()
        self.llm_endpoint = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-5")
        self.genie_spaces = {
            "domain1": os.environ.get("DOMAIN1_GENIE_SPACE_ID", ""),
            "domain2": os.environ.get("DOMAIN2_GENIE_SPACE_ID", ""),
        }
        self._graph = None
        self._short_term_memory_available = True
        self._long_term_memory_available = True
    
    def _get_authenticated_client(self):
        """
        Get WorkspaceClient with proper authentication.
        
        CRITICAL: Must detect execution context to avoid OBO in non-serving envs.
        """
        from databricks.sdk import WorkspaceClient
        
        is_model_serving = (
            os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true"
            or os.environ.get("DATABRICKS_SERVING_ENDPOINT") is not None
            or os.environ.get("MLFLOW_DEPLOYMENT_FLAVOR_NAME") == "databricks"
        )
        
        if is_model_serving:
            try:
                from databricks_ai_bridge import ModelServingUserCredentials
                return WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
            except ImportError:
                return WorkspaceClient()
        else:
            return WorkspaceClient()
    
    @mlflow.trace(name="agent_predict", span_type="AGENT")
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """
        Main prediction method.
        
        Args:
            request: ResponsesAgentRequest with input messages and custom_inputs
            
        Returns:
            ResponsesAgentResponse with output text and custom_outputs
        """
        # Parse request
        input_messages = [msg.model_dump() for msg in request.input]
        query = input_messages[-1].get("content", "")
        custom_inputs = request.custom_inputs or {}
        user_id = custom_inputs.get("user_id", "unknown")
        
        # Process query (implement your logic here)
        response_text = self._process(query, custom_inputs)
        
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(
                text=response_text,
                id=str(uuid.uuid4())
            )],
            custom_outputs={
                "source": "agent",
                "user_id": user_id,
            }
        )
    
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """
        Streaming prediction method.
        
        Yields delta events followed by a done event.
        """
        input_messages = [msg.model_dump() for msg in request.input]
        query = input_messages[-1].get("content", "")
        item_id = str(uuid.uuid4())
        
        for chunk in self._process_streaming(query):
            yield ResponsesAgentStreamEvent(
                type="output_item.delta",
                delta=ResponsesAgentStreamEventDelta(
                    type="message_delta",
                    delta=ResponsesAgentMessageContentDelta(
                        type="text",
                        text=chunk
                    )
                ),
                item_id=item_id,
            )
        
        # Final done event
        yield ResponsesAgentStreamEvent(
            type="output_item.done",
            item_id=item_id,
        )
    
    def _process(self, query: str, custom_inputs: dict) -> str:
        """Implement your agent logic here."""
        raise NotImplementedError("Implement _process()")
    
    def _process_streaming(self, query: str):
        """Implement streaming logic here."""
        raise NotImplementedError("Implement _process_streaming()")


# MANDATORY: Set model for MLflow
mlflow.models.set_model(YourDomainAgent())

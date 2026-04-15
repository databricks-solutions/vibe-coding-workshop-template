"""
MCP Tool-Calling Agent — canonical pattern from the Databricks OpenAI MCP notebook.

Copy this file to your project as `agent.py`, then resolve the three TODO blocks:
  1. LLM_ENDPOINT_NAME  — your Foundation Model API endpoint
  2. SYSTEM_PROMPT       — domain-specific instructions
  3. mcp_servers list    — one McpServerToolkit per Genie Space (or other MCP server)

Source: https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html
"""

import json
from typing import Any, Generator
from uuid import uuid4

import mlflow
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)

from databricks.sdk import WorkspaceClient
from databricks_openai import DatabricksOpenAI, McpServerToolkit

import nest_asyncio

nest_asyncio.apply()

# ── ModelConfig ──────────────────────────────────────────────────────────────
# Reads values from agent-config.yaml (development) or from overrides at
# log_model() time (production). Keeps the class code environment-agnostic.
config = mlflow.models.ModelConfig(development_config="agent-config.yaml")

############################################
# TODO 1: Verify the LLM endpoint name in agent-config.yaml
############################################
LLM_ENDPOINT_NAME = config.get("llm_endpoint")

############################################
# TODO 2: Customize the system prompt in agent-config.yaml
############################################
SYSTEM_PROMPT = config.get("system_prompt")

############################################
# TODO 3: Update Genie Space entries in agent-config.yaml
#          Each entry needs a real space_id from your workspace.
############################################
workspace_client = WorkspaceClient()
host = workspace_client.config.host

genie_spaces = config.get("genie_spaces")
mcp_servers = [
    McpServerToolkit(
        url=f"{host}/api/2.0/mcp/genie/{space['space_id']}",
        name=space.get("name", f"genie_{i}"),
    )
    for i, space in enumerate(genie_spaces)
]


# ── Agent class (verbatim from canonical notebook) ───────────────────────────
class MCPToolCallingAgent(ResponsesAgent):
    def __init__(
        self,
        llm_endpoint: str,
        mcp_servers: list[McpServerToolkit],
    ):
        self.llm_endpoint = llm_endpoint
        self.workspace_client = WorkspaceClient()
        self.model_serving_client = DatabricksOpenAI()
        self.mcp_servers = mcp_servers
        self.tools_dict = {}

        for mcp_server in mcp_servers:
            tool_infos = mcp_server.get_tools()
            for tool_info in tool_infos:
                if tool_info.name in self.tools_dict:
                    raise ValueError(
                        f"Tool Name {tool_info.name} already exists. "
                        f"For MCP Server: {mcp_server.name or mcp_server.url}, "
                        f"specify a new mcp server name to make the tool names unique."
                    )
                self.tools_dict[tool_info.name] = tool_info

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        return self.tools_dict[tool_name].execute(**args)

    @mlflow.trace(span_type=SpanType.LLM)
    def call_llm(
        self, messages: list[dict[str, Any]]
    ) -> Generator[dict[str, Any], None, None]:
        for chunk in self.model_serving_client.chat.completions.create(
            model=self.llm_endpoint,
            messages=to_chat_completions_input(messages),
            tools=[tool.spec for tool in self.tools_dict.values()],
            stream=True,
        ):
            yield chunk.to_dict()

    def handle_tool_call(
        self, tool_call: dict[str, Any], messages: list[dict[str, Any]]
    ) -> ResponsesAgentStreamEvent:
        if tool_call["arguments"]:
            args = json.loads(tool_call["arguments"])
        else:
            args = {}
        result = str(self.execute_tool(tool_name=tool_call["name"], args=args))

        tool_call_output = self.create_function_call_output_item(
            tool_call["call_id"], result
        )
        messages.append(tool_call_output)
        return ResponsesAgentStreamEvent(
            type="response.output_item.done", item=tool_call_output
        )

    def call_and_run_tools(
        self,
        messages: list[dict[str, Any]],
        max_iter: int = 10,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                yield from output_to_responses_items_stream(
                    chunks=self.call_llm(messages), aggregator=messages
                )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item(
                "Max iterations reached. Stopping.", str(uuid4())
            ),
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            output=outputs, custom_outputs=request.custom_inputs
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = [i.model_dump() for i in request.input]
        yield from self.call_and_run_tools(messages)


# ── Autologging + model binding ──────────────────────────────────────────────
mlflow.openai.autolog()
AGENT = MCPToolCallingAgent(llm_endpoint=LLM_ENDPOINT_NAME, mcp_servers=mcp_servers)
mlflow.models.set_model(AGENT)

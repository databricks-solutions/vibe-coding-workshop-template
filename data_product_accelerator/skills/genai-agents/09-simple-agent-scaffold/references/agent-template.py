"""
MCP Tool-Calling Agent — OBO-first pattern (proven end-to-end on Managed MCP).

Copy this file to your project as `agent.py`, then resolve the three TODO blocks
in `agent-config.yaml`:
  1. llm_endpoint   — your Foundation Model API endpoint
  2. system_prompt  — domain-specific instructions
  3. genie_spaces   — one entry per Genie Space (each needs a real space_id)

Authentication contract (do NOT change without re-reading the references):
  - The LLM call uses the endpoint SYSTEM service principal (declared via
    DatabricksServingEndpoint in SystemAuthPolicy at log_model() time).
  - The Genie MCP call uses ON-BEHALF-OF (OBO) the calling user — the agent
    builds an OBO WorkspaceClient PER REQUEST and hands it to McpServerToolkit.
    OBO requires UserAuthPolicy(api_scopes=["mcp.genie", "sql"]) and
    `databricks-ai-bridge` in pip_requirements (see the deploy notebook).
  - When no user token is present (true machine-to-machine callers), the client
    falls back to the system SP. That fallback path is best-effort: it needs UC
    SELECT/EXECUTE on the Genie Space's tables/functions, which the platform does
    NOT auto-grant. Interactive / user-forwarded callers should never hit it.

Build the McpServerToolkit per request (NOT at module load): a toolkit built at
import time hard-binds whatever identity existed then (the system SP), which
defeats OBO. See:
  references/obo-authentication.md
  genai-agents/.../references/model-serving-auth-passthrough.md
Source: https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html
"""

import json
import os
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
GENIE_SPACES = config.get("genie_spaces")


def _obo_client() -> WorkspaceClient:
    """Return a per-request WorkspaceClient with the correct identity.

    In Model Serving with a forwarded user token, returns an OBO client so the
    Genie MCP call runs as the calling user (respecting their UC grants, row
    filters, and column masks). On any failure — true M2M callers with no user
    token, missing `databricks-ai-bridge`, or outside Model Serving — falls back
    to the default client (the endpoint system SP). The fallback is best-effort
    and depends on the SP having UC SELECT/EXECUTE on the Genie tables.
    """
    if os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true":
        try:
            from databricks_ai_bridge import ModelServingUserCredentials

            client = WorkspaceClient(
                credentials_strategy=ModelServingUserCredentials()
            )
            print("auth=OBO (Model Serving user identity)")
            return client
        except ImportError:
            print("auth=SYSTEM_SP (databricks-ai-bridge not installed)")
        except Exception as e:  # noqa: BLE001 — degrade, never crash the request
            print(f"auth=SYSTEM_SP (OBO unavailable: {type(e).__name__}: {e})")
    return WorkspaceClient()


# ── Agent class ──────────────────────────────────────────────────────────────
class MCPToolCallingAgent(ResponsesAgent):
    def __init__(self, llm_endpoint: str, genie_spaces: list[dict]):
        self.llm_endpoint = llm_endpoint
        self.genie_spaces = genie_spaces
        # LLM client uses the endpoint system SP (declared via
        # DatabricksServingEndpoint). It is identity-stable across requests, so
        # it is fine to build once.
        self.model_serving_client = DatabricksOpenAI()

    def _build_tools(self, ws: WorkspaceClient) -> dict[str, Any]:
        """Build the Genie MCP toolkit(s) with the per-request OBO identity."""
        host = ws.config.host
        tools_dict: dict[str, Any] = {}
        for i, space in enumerate(self.genie_spaces):
            toolkit = McpServerToolkit(
                url=f"{host}/api/2.0/mcp/genie/{space['space_id']}",
                name=space.get("name", f"genie_{i}"),
                workspace_client=ws,  # per-request OBO identity
            )
            for tool_info in toolkit.get_tools():
                if tool_info.name in tools_dict:
                    raise ValueError(
                        f"Tool Name {tool_info.name} already exists. "
                        f"For MCP Server: {toolkit.name or toolkit.url}, "
                        f"specify a new mcp server name to make tool names unique."
                    )
                tools_dict[tool_info.name] = tool_info
        return tools_dict

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tools_dict: dict, tool_name: str, args: dict) -> Any:
        return tools_dict[tool_name].execute(**args)

    @mlflow.trace(span_type=SpanType.LLM)
    def call_llm(
        self, messages: list[dict[str, Any]], tools_dict: dict
    ) -> Generator[dict[str, Any], None, None]:
        for chunk in self.model_serving_client.chat.completions.create(
            model=self.llm_endpoint,
            messages=to_chat_completions_input(messages),
            tools=[tool.spec for tool in tools_dict.values()],
            stream=True,
        ):
            yield chunk.to_dict()

    def handle_tool_call(
        self,
        tool_call: dict[str, Any],
        messages: list[dict[str, Any]],
        tools_dict: dict,
    ) -> ResponsesAgentStreamEvent:
        if tool_call["arguments"]:
            args = json.loads(tool_call["arguments"])
        else:
            args = {}
        result = str(
            self.execute_tool(
                tools_dict=tools_dict, tool_name=tool_call["name"], args=args
            )
        )

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
        tools_dict: dict,
        max_iter: int = 10,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages, tools_dict)
            else:
                yield from output_to_responses_items_stream(
                    chunks=self.call_llm(messages, tools_dict), aggregator=messages
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
        # Build the OBO identity and its MCP toolkit PER REQUEST so each call runs
        # as the invoking user (or the system SP for true M2M callers).
        ws = _obo_client()
        tools_dict = self._build_tools(ws)
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}] if SYSTEM_PROMPT else []
        ) + [i.model_dump() for i in request.input]
        yield from self.call_and_run_tools(messages, tools_dict)


# ── Autologging + model binding ──────────────────────────────────────────────
mlflow.openai.autolog()
AGENT = MCPToolCallingAgent(llm_endpoint=LLM_ENDPOINT_NAME, genie_spaces=GENIE_SPACES)
mlflow.models.set_model(AGENT)

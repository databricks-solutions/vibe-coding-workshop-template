"""
Agent Skills - LLM Call Executor
=================================

Executes LLM-based skills by calling Databricks model serving endpoints.
Supports inline prompts and Databricks Prompt Registry.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import PromptSource, SkillManifest

logger = logging.getLogger(__name__)


class LLMCallExecutor(BaseExecutor):
    """
    Executor for LLM-based skills.

    Calls a Databricks model serving endpoint with a system prompt
    (from manifest or Prompt Registry) and user-provided inputs.
    """

    def __init__(self, manifest: SkillManifest):
        super().__init__(manifest)
        self._workspace_client = None
        self._system_prompt: Optional[str] = None

    def _get_workspace_client(self):
        """Lazy-load the Databricks WorkspaceClient."""
        if self._workspace_client is None:
            from databricks.sdk import WorkspaceClient
            self._workspace_client = WorkspaceClient()
        return self._workspace_client

    def _get_system_prompt(self) -> str:
        """Load the system prompt from the configured source."""
        if self._system_prompt is not None:
            return self._system_prompt

        prompt_config = self.manifest.config.prompt
        if not prompt_config:
            self._system_prompt = "You are a helpful assistant."
            return self._system_prompt

        if prompt_config.source == PromptSource.INLINE:
            self._system_prompt = prompt_config.inline_text or "You are a helpful assistant."

        elif prompt_config.source == PromptSource.REGISTRY:
            self._system_prompt = self._load_from_registry(
                prompt_config.registry_uri or "",
                prompt_config.version,
            )

        elif prompt_config.source == PromptSource.FILE:
            self._system_prompt = self._load_from_file(prompt_config.file_path or "")

        else:
            self._system_prompt = "You are a helpful assistant."

        return self._system_prompt

    def _load_from_registry(self, uri: str, version: Optional[int] = None) -> str:
        """Load a prompt from Databricks Prompt Registry."""
        try:
            ws = self._get_workspace_client()
            # Parse URI: prompts:/catalog.schema.name/version
            parts = uri.replace("prompts:/", "").split("/")
            prompt_name = parts[0]
            prompt_version = int(parts[1]) if len(parts) > 1 else (version or 1)

            response = ws.api_client.do(
                "GET",
                f"/api/2.0/mlflow/unity-catalog/prompts/{prompt_name}/versions/{prompt_version}",
            )
            template = response.get("prompt_version", {}).get("template", "")
            logger.info(f"[LLMExecutor] Loaded prompt from registry: {prompt_name}/v{prompt_version}")
            return template or "You are a helpful assistant."

        except Exception as e:
            logger.error(f"[LLMExecutor] Failed to load prompt from registry: {e}")
            return "You are a helpful assistant."

    def _load_from_file(self, file_path: str) -> str:
        """Load a prompt from a local file."""
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[LLMExecutor] Failed to load prompt from file: {e}")
            return "You are a helpful assistant."

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LLM call."""
        ws = self._get_workspace_client()
        system_prompt = self._get_system_prompt()

        # Build user message from inputs
        user_content = self._build_user_message(inputs)

        # Resolve endpoint name from config
        endpoint_url = self._resolve_env_var(self.manifest.config.endpoint or "")
        endpoint_name = endpoint_url.split("/serving-endpoints/")[-1].split("/")[0]

        temperature = self.manifest.config.temperature or 0.2
        max_tokens = self.manifest.config.max_tokens or 1024

        logger.info(f"[LLMExecutor] Calling endpoint: {endpoint_name}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = ws.serving_endpoints.query(
            name=endpoint_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extract text
        response_text = ""
        if hasattr(response, "choices") and response.choices:
            response_text = response.choices[0].message.content
        elif isinstance(response, dict) and "choices" in response:
            response_text = response["choices"][0]["message"]["content"]
        else:
            response_text = str(response)

        # Parse JSON from response
        return self._parse_json_output(response_text, inputs)

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock LLM output."""
        time.sleep(0.3)

        user_query = inputs.get("user_query", inputs.get("query", ""))
        snippets = inputs.get("snippets", [])

        # If this is a summarizer skill
        if snippets:
            return {
                "summary": "Based on web search results, there are several well-reviewed hotels in the area that match your criteria.",
                "suggestions": [
                    {"name": "Suggested Hotel A", "reason": "Highly rated, great location", "source": "Web search"},
                    {"name": "Suggested Hotel B", "reason": "Good value, walkable", "source": "Web search"},
                ],
            }

        # Default: query rewriter
        location = "Miami, FL"
        if "tahoe" in user_query.lower():
            location = "Lake Tahoe, CA"
        elif "austin" in user_query.lower():
            location = "Austin, TX"

        return {
            "rewritten_query": f"Find highly-rated hotels in {location} under $300/night with good amenities",
            "assumptions": [f"Looking for hotels in {location}", "User prefers walkable locations"],
            "missing_info_questions": ["Do you have specific dates in mind?"],
        }

    def _build_user_message(self, inputs: Dict[str, Any]) -> str:
        """Build the user message from inputs."""
        parts = []
        for key, value in inputs.items():
            if isinstance(value, (list, dict)):
                if key == "snippets" and isinstance(value, list):
                    snippets_text = "\n\n".join(
                        [f"[{i + 1}] {s}" for i, s in enumerate(value[:10])]
                    )
                    parts.append(f"Web search results:\n{snippets_text}")
                else:
                    parts.append(f"{key}: {json.dumps(value)}")
            elif value is not None:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)

    def _parse_json_output(
        self, response_text: str, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse JSON from the LLM response, with fallback."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON within the text
            json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        # Last resort: wrap raw text
        logger.warning(f"[LLMExecutor] Could not parse JSON, wrapping raw text")
        first_output = self.manifest.output_schema[0].name if self.manifest.output_schema else "result"
        return {first_output: response_text.strip()[:500]}

"""
Agent Skills - Prompt Registry Executor
=========================================

Fetches prompts from Databricks Prompt Registry (Unity Catalog) and
optionally renders them with template variables.
"""

import logging
import re
from typing import Any, Dict, Optional

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import SkillManifest

logger = logging.getLogger(__name__)


class PromptRegistryExecutor(BaseExecutor):
    """
    Executor that loads and renders prompts from Databricks Prompt Registry.

    The prompt is fetched from Unity Catalog using the Databricks SDK,
    then template variables (e.g., {{location}}) are substituted from inputs.
    """

    def __init__(self, manifest: SkillManifest):
        super().__init__(manifest)
        self._workspace_client = None

    def _get_workspace_client(self):
        """Lazy-load the Databricks WorkspaceClient."""
        if self._workspace_client is None:
            from databricks.sdk import WorkspaceClient
            self._workspace_client = WorkspaceClient()
        return self._workspace_client

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch prompt from registry and render with inputs."""
        prompt_uri = inputs.get("prompt_uri", "")
        if not prompt_uri:
            # Try from config
            prompt_config = self.manifest.config.prompt
            if prompt_config and prompt_config.registry_uri:
                prompt_uri = prompt_config.registry_uri

        if not prompt_uri:
            return {"error": "No prompt_uri provided", "rendered_prompt": ""}

        # Parse URI
        parts = prompt_uri.replace("prompts:/", "").split("/")
        prompt_name = parts[0]
        prompt_version = int(parts[1]) if len(parts) > 1 else 1

        logger.info(f"[PromptRegistryExecutor] Fetching {prompt_name}/v{prompt_version}")

        ws = self._get_workspace_client()

        try:
            response = ws.api_client.do(
                "GET",
                f"/api/2.0/mlflow/unity-catalog/prompts/{prompt_name}/versions/{prompt_version}",
            )

            prompt_version_data = response.get("prompt_version", {})
            template = prompt_version_data.get("template", "")
            name = prompt_version_data.get("name", prompt_name)
            version = prompt_version_data.get("version", prompt_version)

            # Render template variables from inputs
            rendered = self._render_template(template, inputs.get("variables", {}))

            return {
                "prompt_name": name,
                "prompt_version": version,
                "raw_template": template,
                "rendered_prompt": rendered,
                "description": prompt_version_data.get("description", ""),
            }

        except Exception as e:
            logger.error(f"[PromptRegistryExecutor] Failed to fetch prompt: {e}")
            return {
                "error": str(e),
                "rendered_prompt": "",
            }

    def _render_template(
        self, template: str, variables: Dict[str, Any]
    ) -> str:
        """
        Replace {{variable}} placeholders with values from variables dict.
        """
        if not variables:
            return template

        rendered = template
        for key, value in variables.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            rendered = re.sub(pattern, str(value), rendered)

        return rendered

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return a mock prompt."""
        return {
            "prompt_name": "mock_prompt",
            "prompt_version": 1,
            "raw_template": "You are a helpful {{role}} assistant.",
            "rendered_prompt": "You are a helpful travel assistant.",
            "description": "Mock prompt for testing",
        }

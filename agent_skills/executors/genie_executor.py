"""
Agent Skills - Genie Query Executor
=====================================

Executes Genie Space queries using the Databricks SDK.
Handles conversation lifecycle, polling, and response parsing.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import SkillManifest

logger = logging.getLogger(__name__)


class GenieQueryExecutor(BaseExecutor):
    """
    Executor for Databricks Genie Space queries.

    Starts a Genie conversation, polls for completion, and parses
    the structured response into items and answer text.
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
        """Execute a Genie Space query."""
        ws = self._get_workspace_client()
        query_text = inputs["query_text"]
        space_id = self._resolve_env_var(self.manifest.config.space_id or "")
        timeout = self.manifest.config.timeout_seconds or 60
        max_retries = self.manifest.config.max_retries or 1

        logger.info(f"[GenieExecutor] Querying space {space_id}: {query_text[:80]}...")

        retries = 0
        last_error = None

        while retries <= max_retries:
            try:
                result = self._run_query(ws, space_id, query_text, timeout)
                return result
            except Exception as e:
                retries += 1
                last_error = str(e)
                logger.warning(f"[GenieExecutor] Attempt {retries} failed: {e}")
                if retries > max_retries:
                    break
                time.sleep(1)

        return {
            "answer_text": None,
            "items": [],
            "genie_status": "error",
            "error": last_error or "Max retries exceeded",
        }

    def _run_query(
        self, ws: Any, space_id: str, query_text: str, timeout: int
    ) -> Dict[str, Any]:
        """Run a single Genie query with polling."""
        conversation = ws.genie.start_conversation(
            space_id=space_id,
            content=query_text,
        )

        conversation_id = conversation.conversation_id
        message_id = conversation.message_id

        logger.info(f"[GenieExecutor] Conversation: {conversation_id}, message: {message_id}")

        # Poll for result
        poll_start = time.time()
        while time.time() - poll_start < timeout:
            message = ws.genie.get_message(
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )

            status = (
                message.status.value
                if hasattr(message.status, "value")
                else str(message.status)
            )

            if status in ("COMPLETED", "completed"):
                return self._parse_response(message)
            elif status in ("FAILED", "failed", "ERROR", "error"):
                error_msg = getattr(message, "error", "Unknown error")
                return {
                    "answer_text": None,
                    "items": [],
                    "genie_status": "error",
                    "error": str(error_msg),
                }
            else:
                time.sleep(2)

        return {
            "answer_text": None,
            "items": [],
            "genie_status": "error",
            "error": f"Timed out after {timeout}s",
        }

    def _parse_response(self, message: Any) -> Dict[str, Any]:
        """Parse a completed Genie response."""
        answer_text = None
        items: List[Dict[str, Any]] = []

        if hasattr(message, "attachments") and message.attachments:
            for attachment in message.attachments:
                # Text content
                if hasattr(attachment, "text") and attachment.text:
                    if hasattr(attachment.text, "content"):
                        answer_text = attachment.text.content

                # Query results (table data)
                if hasattr(attachment, "query") and attachment.query:
                    query_result = attachment.query
                    if hasattr(query_result, "result") and query_result.result:
                        result = query_result.result
                        if hasattr(result, "data_array") and result.data_array:
                            columns = []
                            if hasattr(result, "schema") and result.schema:
                                columns = [col.name for col in result.schema.columns]

                            for row in result.data_array:
                                if columns:
                                    item = {
                                        columns[i]: row[i]
                                        for i in range(min(len(columns), len(row)))
                                    }
                                else:
                                    item = {"data": row}
                                items.append(item)

        if not answer_text and not items:
            return {
                "answer_text": "I couldn't find relevant information for your query.",
                "items": [],
                "genie_status": "no_answer",
            }

        logger.info(f"[GenieExecutor] Success: {len(items)} items found")
        return {
            "answer_text": answer_text,
            "items": items,
            "genie_status": "ok",
        }

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock Genie results."""
        time.sleep(0.5)
        return {
            "answer_text": "Based on your preferences, I found several highly-rated hotels that match your criteria.",
            "items": [
                {
                    "id": "stay_mock_1",
                    "name": "Grand Miami Resort & Spa",
                    "location": "Miami Beach, FL",
                    "price_per_night": 289,
                    "rating": 4.8,
                    "highlights": ["Ocean view", "Near concert venues", "Pool access"],
                },
                {
                    "id": "stay_mock_2",
                    "name": "Downtown Miami Luxury Hotel",
                    "location": "Downtown Miami, FL",
                    "price_per_night": 245,
                    "rating": 4.6,
                    "highlights": ["Walking distance to events", "Rooftop bar", "Free breakfast"],
                },
                {
                    "id": "stay_mock_3",
                    "name": "Beachside Boutique Inn",
                    "location": "South Beach, FL",
                    "price_per_night": 199,
                    "rating": 4.5,
                    "highlights": ["Beach access", "Cozy atmosphere", "Great reviews"],
                },
            ],
            "genie_status": "ok",
        }

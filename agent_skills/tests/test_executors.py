"""
Tests for Skill Executors
===========================

Unit tests for individual executor types using mock mode.
"""

import asyncio
import pytest

from agent_skills.models import (
    FallbackConfig,
    FallbackStrategy,
    FieldSchema,
    SkillConfig,
    SkillManifest,
    SkillStatus,
    SkillType,
)
from agent_skills.executors.llm_executor import LLMCallExecutor
from agent_skills.executors.genie_executor import GenieQueryExecutor
from agent_skills.executors.web_search_executor import WebSearchExecutor
from agent_skills.executors.function_executor import FunctionExecutor
from agent_skills.executors.lakebase_executor import LakebaseQueryExecutor


# =============================================================================
# Helper to create manifests
# =============================================================================

def make_manifest(
    skill_id: str,
    skill_type: SkillType,
    config: dict = None,
    inputs: list = None,
    outputs: list = None,
    fallback: dict = None,
) -> SkillManifest:
    return SkillManifest(
        skill_id=skill_id,
        name=f"Test {skill_id}",
        type=skill_type,
        config=SkillConfig(**(config or {})),
        input_schema=[FieldSchema(**f) for f in (inputs or [])],
        output_schema=[FieldSchema(**f) for f in (outputs or [])],
        fallback=FallbackConfig(**(fallback or {})),
        mock_enabled=True,
    )


def run_async(coro):
    """Helper to run async tests without pytest-asyncio."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# LLM Executor Tests
# =============================================================================

class TestLLMCallExecutor:
    """Tests for LLMCallExecutor mock mode."""

    def test_mock_query_rewrite(self):
        """Mock LLM should return rewritten query."""
        manifest = make_manifest(
            "test_llm",
            SkillType.LLM_CALL,
            inputs=[{"name": "user_query", "type": "string", "required": True}],
            outputs=[{"name": "rewritten_query", "type": "string"}],
        )
        executor = LLMCallExecutor(manifest)
        result = run_async(executor.execute(
            {"user_query": "hotels in miami"},
            step_id="test",
            mock_mode=True,
        ))
        assert result.status == SkillStatus.SUCCESS
        assert "rewritten_query" in result.output
        assert "Miami" in result.output["rewritten_query"]

    def test_mock_summarizer(self):
        """Mock LLM should return summary when snippets are provided."""
        manifest = make_manifest(
            "test_summarizer",
            SkillType.LLM_CALL,
            inputs=[
                {"name": "snippets", "type": "list", "required": True},
                {"name": "user_query", "type": "string", "required": True},
            ],
            outputs=[
                {"name": "summary", "type": "string"},
                {"name": "suggestions", "type": "list"},
            ],
        )
        executor = LLMCallExecutor(manifest)
        result = run_async(executor.execute(
            {"snippets": ["snippet 1", "snippet 2"], "user_query": "hotels"},
            step_id="test",
            mock_mode=True,
        ))
        assert result.status == SkillStatus.SUCCESS
        assert "summary" in result.output


# =============================================================================
# Genie Executor Tests
# =============================================================================

class TestGenieQueryExecutor:
    """Tests for GenieQueryExecutor mock mode."""

    def test_mock_genie_query(self):
        """Mock Genie should return items and answer."""
        manifest = make_manifest(
            "test_genie",
            SkillType.GENIE_QUERY,
            config={"space_id": "test_space"},
            inputs=[{"name": "query_text", "type": "string", "required": True}],
            outputs=[
                {"name": "answer_text", "type": "string"},
                {"name": "items", "type": "list"},
                {"name": "genie_status", "type": "string"},
            ],
        )
        executor = GenieQueryExecutor(manifest)
        result = run_async(executor.execute(
            {"query_text": "hotels in miami"},
            step_id="test",
            mock_mode=True,
        ))
        assert result.status == SkillStatus.SUCCESS
        assert result.output["genie_status"] == "ok"
        assert len(result.output["items"]) > 0


# =============================================================================
# Web Search Executor Tests
# =============================================================================

class TestWebSearchExecutor:
    """Tests for WebSearchExecutor mock mode."""

    def test_mock_web_search(self):
        """Mock web search should return snippets."""
        manifest = make_manifest(
            "test_web",
            SkillType.WEB_SEARCH,
            config={"provider": "serpapi", "api_key_env": "WEB_SEARCH_API_KEY"},
            inputs=[{"name": "query", "type": "string", "required": True}],
            outputs=[
                {"name": "snippets", "type": "list"},
                {"name": "links", "type": "list"},
                {"name": "search_status", "type": "string"},
            ],
        )
        executor = WebSearchExecutor(manifest)
        result = run_async(executor.execute(
            {"query": "hotels in miami"},
            step_id="test",
            mock_mode=True,
        ))
        assert result.status == SkillStatus.SUCCESS
        assert result.output["search_status"] == "ok"
        assert len(result.output["snippets"]) > 0


# =============================================================================
# Function Executor Tests
# =============================================================================

class TestFunctionExecutor:
    """Tests for FunctionExecutor."""

    def test_builtin_function(self):
        """Should execute built-in functions."""
        manifest = make_manifest(
            "test_func",
            SkillType.FUNCTION,
            config={
                "module_path": "agent_skills.executors.function_executor",
                "function_name": "extract_location_hint",
            },
            inputs=[{"name": "query_text", "type": "string", "required": True}],
            outputs=[{"name": "location", "type": "string"}],
        )
        executor = FunctionExecutor(manifest)
        result = run_async(executor.execute(
            {"query_text": "Find hotels in Austin Texas"},
            step_id="test",
        ))
        assert result.status == SkillStatus.SUCCESS
        assert result.output["location"] == "Austin"

    def test_missing_required_input(self):
        """Should handle missing required inputs."""
        manifest = make_manifest(
            "test_func",
            SkillType.FUNCTION,
            config={"function_name": "extract_location_hint"},
            inputs=[{"name": "query_text", "type": "string", "required": True}],
            fallback={"strategy": "skip"},
        )
        executor = FunctionExecutor(manifest)
        result = run_async(executor.execute(
            {},  # Missing required input
            step_id="test",
        ))
        assert result.status == SkillStatus.SKIPPED


# =============================================================================
# Fallback Tests
# =============================================================================

class TestFallbackHandling:
    """Tests for fallback strategies across executors."""

    def test_default_value_fallback(self):
        """Should return default value on failure."""
        manifest = make_manifest(
            "test_default",
            SkillType.FUNCTION,
            config={"function_name": "nonexistent_function"},
            inputs=[{"name": "input", "type": "string", "required": True}],
            fallback={
                "strategy": "default_value",
                "default_value": {"result": "fallback_data"},
            },
        )
        executor = FunctionExecutor(manifest)
        result = run_async(executor.execute(
            {"input": "test"},
            step_id="test",
        ))
        assert result.status == SkillStatus.FAILURE
        assert result.output["result"] == "fallback_data"

    def test_skip_fallback(self):
        """Should skip on failure with skip strategy."""
        manifest = make_manifest(
            "test_skip",
            SkillType.FUNCTION,
            config={"function_name": "nonexistent_function"},
            inputs=[{"name": "input", "type": "string", "required": True}],
            fallback={"strategy": "skip"},
        )
        executor = FunctionExecutor(manifest)
        result = run_async(executor.execute(
            {"input": "test"},
            step_id="test",
        ))
        assert result.status == SkillStatus.SKIPPED

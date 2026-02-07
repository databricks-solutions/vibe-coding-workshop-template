"""
Tests for FlowEngine
======================

Verifies variable resolution, condition evaluation, and flow execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_skills.engine import FlowEngine
from agent_skills.models import (
    FlowDefinition,
    FlowStep,
    ResponseMapping,
    SkillManifest,
    SkillResult,
    SkillStatus,
    SkillType,
    StepInput,
)


@pytest.fixture
def mock_registry():
    """Create a mock registry with test skills and flows."""
    registry = MagicMock()

    # Mock skill
    skill = SkillManifest(
        skill_id="test_skill",
        name="Test Skill",
        type=SkillType.FUNCTION,
    )
    registry.get_skill.return_value = skill

    # Mock flow
    flow = FlowDefinition(
        flow_id="test_flow",
        name="Test Flow",
        steps=[
            FlowStep(
                skill="test_skill",
                id="step1",
                inputs=[
                    StepInput(field="query", reference="${request.message}"),
                ],
            ),
        ],
        response=[
            ResponseMapping(field="result", reference="${step1.output.data}"),
            ResponseMapping(field="fallback_field", reference="${missing.output.data}", default="default_value"),
        ],
    )
    registry.get_flow.return_value = flow

    return registry


@pytest.fixture
def engine(mock_registry):
    """Create a FlowEngine with mock registry."""
    return FlowEngine(mock_registry)


class TestVariableResolution:
    """Tests for variable reference resolution."""

    def test_resolve_request_reference(self, engine):
        """Should resolve ${request.field} references."""
        context = {"request": {"message": "hello world"}, "steps": {}}
        value = engine._resolve_reference("${request.message}", context)
        assert value == "hello world"

    def test_resolve_step_output_reference(self, engine):
        """Should resolve ${step_id.output.field} references."""
        context = {
            "request": {},
            "steps": {
                "step1": {"output": {"data": "result_data"}, "status": "success"}
            },
        }
        value = engine._resolve_reference("${step1.output.data}", context)
        assert value == "result_data"

    def test_resolve_missing_reference(self, engine):
        """Should return None for missing references."""
        context = {"request": {}, "steps": {}}
        value = engine._resolve_reference("${missing.output.field}", context)
        assert value is None

    def test_resolve_string_vars(self, engine):
        """Should replace embedded ${} patterns in strings."""
        context = {"request": {"name": "Miami"}, "steps": {}}
        result = engine._resolve_string_vars("Search for ${request.name}", context)
        assert result == "Search for Miami"


class TestConditionEvaluation:
    """Tests for condition expression evaluation."""

    def test_equality_condition_true(self, engine):
        """Should evaluate equality as true when values match."""
        context = {
            "request": {},
            "steps": {"genie": {"output": {"status": "ok"}, "status": "success"}},
        }
        result = engine._evaluate_condition(
            '${genie.output.status} == "ok"', context
        )
        assert result is True

    def test_equality_condition_false(self, engine):
        """Should evaluate equality as false when values don't match."""
        context = {
            "request": {},
            "steps": {"genie": {"output": {"status": "error"}, "status": "success"}},
        }
        result = engine._evaluate_condition(
            '${genie.output.status} == "ok"', context
        )
        assert result is False

    def test_inequality_condition(self, engine):
        """Should evaluate != conditions."""
        context = {
            "request": {},
            "steps": {"genie": {"output": {"status": "error"}, "status": "failure"}},
        }
        result = engine._evaluate_condition(
            '${genie.output.status} != "ok"', context
        )
        assert result is True

    def test_condition_with_missing_reference(self, engine):
        """Should return False when condition references missing data."""
        context = {"request": {}, "steps": {}}
        result = engine._evaluate_condition(
            '${missing.output.field} == "ok"', context
        )
        assert result is False


class TestResponseMapping:
    """Tests for response building from flow mappings."""

    def test_build_response_with_references(self, engine):
        """Should build response from step outputs."""
        flow = FlowDefinition(
            flow_id="test",
            name="Test",
            response=[
                ResponseMapping(field="answer", reference="${step1.output.text}"),
                ResponseMapping(field="count", reference="${step1.output.count}", default=0),
            ],
        )
        context = {
            "request": {},
            "steps": {"step1": {"output": {"text": "hello", "count": 5}, "status": "success"}},
        }
        response = engine._build_response(flow, context)
        assert response["answer"] == "hello"
        assert response["count"] == 5

    def test_build_response_with_defaults(self, engine):
        """Should use defaults when references are missing."""
        flow = FlowDefinition(
            flow_id="test",
            name="Test",
            response=[
                ResponseMapping(field="missing", reference="${none.output.field}", default="fallback"),
            ],
        )
        context = {"request": {}, "steps": {}}
        response = engine._build_response(flow, context)
        assert response["missing"] == "fallback"


class TestFunctionExecutor:
    """Tests for the built-in function executor."""

    def test_extract_location_hint(self):
        """Should extract known locations from text."""
        from agent_skills.executors.function_executor import extract_location_hint

        result = extract_location_hint("Find hotels in Miami for the weekend")
        assert result["location"] == "Miami"

    def test_extract_location_unknown(self):
        """Should return None for unknown locations."""
        from agent_skills.executors.function_executor import extract_location_hint

        result = extract_location_hint("Something with no location")
        assert result["location"] is None

    def test_extract_location_lake_tahoe(self):
        """Should extract multi-word locations."""
        from agent_skills.executors.function_executor import extract_location_hint

        result = extract_location_hint("Cabin near Lake Tahoe for skiing")
        assert result["location"] == "Lake Tahoe"

    def test_calculate_total_price(self):
        """Should calculate booking totals correctly."""
        from agent_skills.executors.function_executor import calculate_total_price

        result = calculate_total_price(
            price_per_night=200, nights=3, cleaning_fee=50,
            service_fee=30, tax_rate=0.1
        )
        assert result["subtotal"] == 600
        assert result["taxes"] == 60
        assert result["total"] == 740

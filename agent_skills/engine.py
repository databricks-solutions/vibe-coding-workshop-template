"""
Agent Skills - Flow Engine
============================

The orchestration engine that executes multi-step flows by:
1. Resolving variable references between steps
2. Evaluating conditions to decide step execution
3. Running executors for each step's skill
4. Mapping results to the final response

Variable Reference Syntax:
    ${request.field}           → Original request input
    ${step_id.output.field}    → Output from a previous step
    ${step_id.status}          → Status of a previous step (success/failure/skipped)
"""

import logging
import os
import re
import time
from typing import Any, Dict, Optional, Type

from agent_skills.models import (
    FlowDefinition,
    FlowResult,
    FlowStep,
    SkillManifest,
    SkillResult,
    SkillStatus,
    SkillType,
    StepInput,
)
from agent_skills.executors.base import BaseExecutor
from agent_skills.executors.llm_executor import LLMCallExecutor
from agent_skills.executors.genie_executor import GenieQueryExecutor
from agent_skills.executors.web_search_executor import WebSearchExecutor
from agent_skills.executors.lakebase_executor import LakebaseQueryExecutor
from agent_skills.executors.function_executor import FunctionExecutor
from agent_skills.executors.prompt_registry_executor import PromptRegistryExecutor

logger = logging.getLogger(__name__)


# Mapping from skill type to executor class
EXECUTOR_MAP: Dict[SkillType, Type[BaseExecutor]] = {
    SkillType.LLM_CALL: LLMCallExecutor,
    SkillType.GENIE_QUERY: GenieQueryExecutor,
    SkillType.WEB_SEARCH: WebSearchExecutor,
    SkillType.LAKEBASE_QUERY: LakebaseQueryExecutor,
    SkillType.FUNCTION: FunctionExecutor,
    SkillType.PROMPT_REGISTRY: PromptRegistryExecutor,
}

# Pattern for variable references: ${path.to.value}
VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class FlowEngine:
    """
    Orchestration engine that executes declarative flow pipelines.

    The engine resolves a flow definition, iterates through its steps,
    evaluates conditions, resolves variable references, runs executors,
    and maps results to the final response.
    """

    def __init__(self, registry: Any):
        """
        Initialize the flow engine.

        Args:
            registry: A SkillRegistry instance for looking up skills and flows.
        """
        self.registry = registry
        self._executor_cache: Dict[str, BaseExecutor] = {}

    async def execute_flow(
        self,
        flow_id: str,
        request: Dict[str, Any],
        mock_mode: Optional[bool] = None,
    ) -> FlowResult:
        """
        Execute a complete flow pipeline.

        Args:
            flow_id: ID of the flow to execute.
            request: The incoming request data (user inputs).
            mock_mode: Override mock mode (defaults to APP_MOCK_MODE env var).

        Returns:
            FlowResult with response data and step-level results.
        """
        start_time = time.time()
        logger.info(f"[FlowEngine] Executing flow: {flow_id}")

        # Resolve mock mode
        if mock_mode is None:
            mock_mode = os.getenv("APP_MOCK_MODE", "false").lower() == "true"

        # Look up the flow
        flow = self.registry.get_flow(flow_id)
        if not flow:
            return FlowResult(
                flow_id=flow_id,
                status=SkillStatus.FAILURE,
                error=f"Flow not found: {flow_id}",
            )

        # Context tracks all step results and the original request
        context: Dict[str, Any] = {
            "request": request,
            "steps": {},
        }
        step_results: Dict[str, SkillResult] = {}

        # Execute steps sequentially (parallel support is a future enhancement)
        for step in flow.steps:
            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, context):
                logger.info(f"[FlowEngine] Skipping step {step.id}: condition not met")
                skip_result = SkillResult(
                    skill_id=step.skill,
                    step_id=step.id,
                    status=SkillStatus.SKIPPED,
                    metadata={"reason": "condition_not_met"},
                )
                step_results[step.id] = skip_result
                context["steps"][step.id] = {
                    "output": {},
                    "status": "skipped",
                }
                continue

            # Resolve inputs for this step
            resolved_inputs = self._resolve_step_inputs(step, context)

            # Get the skill manifest
            skill = self.registry.get_skill(step.skill)
            if not skill:
                logger.error(f"[FlowEngine] Skill not found: {step.skill}")
                err_result = SkillResult(
                    skill_id=step.skill,
                    step_id=step.id,
                    status=SkillStatus.FAILURE,
                    error=f"Skill not found: {step.skill}",
                )
                step_results[step.id] = err_result
                context["steps"][step.id] = {
                    "output": {},
                    "status": "failure",
                }
                continue

            # Get or create executor
            executor = self._get_executor(skill)

            # Execute the skill
            result = await executor.execute(
                inputs=resolved_inputs,
                step_id=step.id,
                mock_mode=mock_mode,
            )

            # Handle passthrough fallback
            if (
                result.status == SkillStatus.FAILURE
                and result.output.get("_fallback") == "passthrough"
            ):
                passthrough_field = result.output.get("_field", "")
                if passthrough_field in resolved_inputs:
                    first_output = (
                        skill.output_schema[0].name if skill.output_schema else "result"
                    )
                    result.output = {first_output: resolved_inputs[passthrough_field]}
                    logger.info(
                        f"[FlowEngine] Passthrough fallback: {passthrough_field} → {first_output}"
                    )

            step_results[step.id] = result
            context["steps"][step.id] = {
                "output": result.output,
                "status": result.status.value,
            }

            logger.info(
                f"[FlowEngine] Step {step.id}: {result.status.value} "
                f"({result.latency_ms}ms)"
            )

        # Build the final response from response mappings
        response = self._build_response(flow, context)

        total_latency = int((time.time() - start_time) * 1000)
        logger.info(f"[FlowEngine] Flow {flow_id} completed in {total_latency}ms")

        return FlowResult(
            flow_id=flow_id,
            status=SkillStatus.SUCCESS,
            response=response,
            step_results=step_results,
            total_latency_ms=total_latency,
            display=flow.display,
        )

    # =========================================================================
    # Variable Resolution
    # =========================================================================

    def _resolve_step_inputs(
        self, step: FlowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve all input fields for a step using context."""
        resolved = {}
        for step_input in step.inputs:
            if step_input.reference:
                value = self._resolve_reference(step_input.reference, context)
            else:
                value = step_input.value

            # Resolve any embedded references in string values
            if isinstance(value, str):
                value = self._resolve_string_vars(value, context)

            resolved[step_input.field] = value
        return resolved

    def _resolve_reference(
        self, reference: str, context: Dict[str, Any]
    ) -> Any:
        """
        Resolve a variable reference like ${step_id.output.field}.

        Supported paths:
            ${request.field}             → context["request"]["field"]
            ${step_id.output.field}      → context["steps"]["step_id"]["output"]["field"]
            ${step_id.status}            → context["steps"]["step_id"]["status"]
        """
        path = reference
        if path.startswith("${") and path.endswith("}"):
            path = path[2:-1]

        parts = path.split(".")
        first = parts[0]

        # Direct top-level keys: "request", "steps"
        if first in context:
            current: Any = context
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    logger.debug(f"[FlowEngine] Cannot resolve reference: {reference}")
                    return None
            return current

        # Step shorthand: step_id.output.field → context["steps"][step_id][...]
        steps = context.get("steps", {})
        if first in steps:
            current = steps[first]
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    logger.debug(f"[FlowEngine] Cannot resolve reference: {reference}")
                    return None
            return current

        logger.debug(f"[FlowEngine] Cannot resolve reference: {reference}")
        return None

    def _resolve_string_vars(self, text: str, context: Dict[str, Any]) -> str:
        """Replace all ${...} patterns in a string with resolved values."""
        def replace_match(match):
            ref = match.group(0)
            value = self._resolve_reference(ref, context)
            return str(value) if value is not None else ref

        return VAR_PATTERN.sub(replace_match, text)

    # =========================================================================
    # Condition Evaluation
    # =========================================================================

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression using the flow context.

        Supported patterns:
            ${step_id.status} == "success"
            ${step_id.output.genie_status} != "ok"
            ${step_id.output.items} is empty
            not ${step_id.status} == "success"
        """
        try:
            # Resolve all variable references in the condition
            resolved = self._resolve_string_vars(condition, context)

            # Handle "is empty" / "is not empty" patterns
            if "is empty" in resolved:
                field_ref = resolved.replace("is empty", "").strip()
                actual_val = self._resolve_reference(
                    condition.split("is empty")[0].strip(), context
                )
                if isinstance(actual_val, (list, dict)):
                    return len(actual_val) == 0
                return not actual_val

            if "is not empty" in resolved:
                field_ref = resolved.replace("is not empty", "").strip()
                actual_val = self._resolve_reference(
                    condition.split("is not empty")[0].strip(), context
                )
                if isinstance(actual_val, (list, dict)):
                    return len(actual_val) > 0
                return bool(actual_val)

            # Handle basic comparison operators
            for op in ["!=", "=="]:
                if op in resolved:
                    left, right = resolved.split(op, 1)
                    left = left.strip().strip('"').strip("'")
                    right = right.strip().strip('"').strip("'")
                    if op == "==":
                        return left == right
                    else:
                        return left != right

            # Handle 'not' prefix
            if resolved.strip().startswith("not "):
                inner = resolved.strip()[4:]
                return not self._evaluate_condition(inner, context)

            # Boolean check
            return bool(resolved)

        except Exception as e:
            logger.warning(f"[FlowEngine] Condition evaluation failed: {condition} → {e}")
            return False

    # =========================================================================
    # Response Building
    # =========================================================================

    def _build_response(
        self, flow: FlowDefinition, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the final response from flow response mappings."""
        response = {}
        for mapping in flow.response:
            if mapping.reference:
                value = self._resolve_reference(mapping.reference, context)
                response[mapping.field] = value if value is not None else mapping.default
            else:
                response[mapping.field] = mapping.default
        return response

    # =========================================================================
    # Executor Management
    # =========================================================================

    def _get_executor(self, skill: SkillManifest) -> BaseExecutor:
        """Get or create an executor for a skill."""
        if skill.skill_id in self._executor_cache:
            return self._executor_cache[skill.skill_id]

        executor_class = EXECUTOR_MAP.get(skill.type)
        if not executor_class:
            raise ValueError(f"No executor for skill type: {skill.type}")

        executor = executor_class(skill)
        self._executor_cache[skill.skill_id] = executor
        return executor

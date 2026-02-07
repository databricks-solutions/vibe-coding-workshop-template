"""
Agent Skills - Base Executor
=============================

Abstract base class for all skill executors. Provides common lifecycle hooks:
- Input validation
- Execution
- Fallback handling
- Mock support
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from agent_skills.models import (
    FallbackStrategy,
    SkillManifest,
    SkillResult,
    SkillStatus,
)

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """
    Abstract base class for skill executors.

    Subclasses implement `_execute()` and optionally `_mock_execute()`.
    The base class handles input validation, timing, fallback, and error handling.
    """

    def __init__(self, manifest: SkillManifest):
        """
        Initialize the executor with a skill manifest.

        Args:
            manifest: The skill's declarative configuration.
        """
        self.manifest = manifest
        self.skill_id = manifest.skill_id

    async def execute(
        self,
        inputs: Dict[str, Any],
        step_id: str = "",
        mock_mode: bool = False,
    ) -> SkillResult:
        """
        Execute the skill with full lifecycle management.

        Args:
            inputs: Resolved input values keyed by field name.
            step_id: The step ID within the flow (for logging).
            mock_mode: Whether to use mock execution.

        Returns:
            SkillResult with output data and metadata.
        """
        start_time = time.time()
        step_label = f"{self.skill_id}" + (f"/{step_id}" if step_id else "")

        logger.info(f"[Executor:{step_label}] Starting execution")
        logger.debug(f"[Executor:{step_label}] Inputs: {list(inputs.keys())}")

        # Validate required inputs
        validation_error = self._validate_inputs(inputs)
        if validation_error:
            logger.error(f"[Executor:{step_label}] Validation failed: {validation_error}")
            return self._handle_fallback(step_id, validation_error, start_time)

        try:
            if mock_mode and self.manifest.mock_enabled:
                logger.info(f"[Executor:{step_label}] Running in MOCK mode")
                output = await self._mock_execute(inputs)
            else:
                output = await self._execute(inputs)

            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[Executor:{step_label}] Completed in {latency_ms}ms")

            return SkillResult(
                skill_id=self.skill_id,
                step_id=step_id,
                status=SkillStatus.SUCCESS,
                output=output,
                latency_ms=latency_ms,
            )

        except TimeoutError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"[Executor:{step_label}] Timed out after {latency_ms}ms")
            return self._handle_fallback(step_id, f"Timeout: {e}", start_time)

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[Executor:{step_label}] Failed: {e}")
            return self._handle_fallback(step_id, str(e), start_time)

    # =========================================================================
    # Template methods for subclasses
    # =========================================================================

    @abstractmethod
    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill logic.

        Args:
            inputs: Validated input values.

        Returns:
            Dict of output field name → value.
        """
        ...

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock execution for development/testing.

        Default implementation returns empty output. Override in subclass.
        """
        return {field.name: field.default for field in self.manifest.output_schema}

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Optional[str]:
        """Validate that all required inputs are present."""
        for field in self.manifest.input_schema:
            if field.required and field.name not in inputs:
                return f"Missing required input: {field.name}"
        return None

    def _handle_fallback(
        self, step_id: str, error: str, start_time: float
    ) -> SkillResult:
        """Apply the manifest's fallback strategy on failure."""
        latency_ms = int((time.time() - start_time) * 1000)
        fb = self.manifest.fallback

        if fb.strategy == FallbackStrategy.PASSTHROUGH and fb.passthrough_field:
            # This will be resolved by the engine from the inputs
            return SkillResult(
                skill_id=self.skill_id,
                step_id=step_id,
                status=SkillStatus.FAILURE,
                output={"_fallback": "passthrough", "_field": fb.passthrough_field},
                error=error,
                latency_ms=latency_ms,
                metadata={"fallback_strategy": "passthrough"},
            )
        elif fb.strategy == FallbackStrategy.DEFAULT_VALUE and fb.default_value is not None:
            default = fb.default_value if isinstance(fb.default_value, dict) else {"result": fb.default_value}
            return SkillResult(
                skill_id=self.skill_id,
                step_id=step_id,
                status=SkillStatus.FAILURE,
                output=default,
                error=error,
                latency_ms=latency_ms,
                metadata={"fallback_strategy": "default_value"},
            )
        else:
            return SkillResult(
                skill_id=self.skill_id,
                step_id=step_id,
                status=SkillStatus.SKIPPED,
                output={},
                error=error,
                latency_ms=latency_ms,
                metadata={"fallback_strategy": "skip"},
            )

    def _resolve_env_var(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns in config values."""
        if value and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.getenv(env_name, value)
        return value

"""
Agent Skills - Function Executor
==================================

Executes arbitrary Python functions defined in skill manifests.
Supports both sync and async functions.
"""

import importlib
import logging
from typing import Any, Callable, Dict, List, Optional

from agent_skills.executors.base import BaseExecutor
from agent_skills.models import SkillManifest

logger = logging.getLogger(__name__)


# =============================================================================
# Built-in utility functions that can be referenced from manifests
# =============================================================================

SUPPORTED_LOCATIONS = [
    "miami", "lake tahoe", "austin", "san diego", "boston",
    "fredericksburg", "new york", "los angeles", "san francisco",
    "seattle", "denver", "chicago", "orlando", "las vegas",
]


def extract_location_hint(query_text: str) -> Dict[str, Any]:
    """
    Extract a location from a query string by matching known locations.

    Args:
        query_text: Text to search for location mentions.

    Returns:
        Dict with "location" key (str or None).
    """
    query_lower = query_text.lower()
    for loc in SUPPORTED_LOCATIONS:
        if loc in query_lower:
            return {"location": loc.title()}
    return {"location": None}


def format_price(amount: float, currency: str = "USD") -> Dict[str, str]:
    """Format a price amount with currency symbol."""
    if currency == "USD":
        return {"formatted": f"${amount:,.2f}"}
    return {"formatted": f"{amount:,.2f} {currency}"}


def calculate_total_price(
    price_per_night: float, nights: int, cleaning_fee: float = 0,
    service_fee: float = 0, tax_rate: float = 0.0
) -> Dict[str, Any]:
    """Calculate total booking price."""
    subtotal = price_per_night * nights
    taxes = subtotal * tax_rate
    total = subtotal + cleaning_fee + service_fee + taxes
    return {
        "subtotal": subtotal,
        "cleaning_fee": cleaning_fee,
        "service_fee": service_fee,
        "taxes": round(taxes, 2),
        "total": round(total, 2),
        "nights": nights,
    }


# Registry of built-in functions
BUILTIN_FUNCTIONS: Dict[str, Callable] = {
    "extract_location_hint": extract_location_hint,
    "format_price": format_price,
    "calculate_total_price": calculate_total_price,
}


# =============================================================================
# Function Executor
# =============================================================================

class FunctionExecutor(BaseExecutor):
    """
    Executor that runs arbitrary Python functions.

    Functions can be built-in (registered above) or dynamically imported
    from a module path specified in the manifest config.
    """

    def __init__(self, manifest: SkillManifest):
        super().__init__(manifest)
        self._func: Optional[Callable] = None

    def _resolve_function(self) -> Callable:
        """Resolve the function from config."""
        if self._func is not None:
            return self._func

        func_name = self.manifest.config.function_name
        module_path = self.manifest.config.module_path

        # Try built-in functions first
        if func_name and func_name in BUILTIN_FUNCTIONS:
            self._func = BUILTIN_FUNCTIONS[func_name]
            logger.info(f"[FunctionExecutor] Using built-in function: {func_name}")
            return self._func

        # Try dynamic import
        if module_path and func_name:
            try:
                module = importlib.import_module(module_path)
                self._func = getattr(module, func_name)
                logger.info(f"[FunctionExecutor] Loaded {func_name} from {module_path}")
                return self._func
            except (ImportError, AttributeError) as e:
                raise RuntimeError(
                    f"Cannot resolve function {module_path}.{func_name}: {e}"
                )

        raise RuntimeError(
            f"No function specified for skill {self.skill_id}. "
            f"Set config.function_name and optionally config.module_path."
        )

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the resolved function."""
        func = self._resolve_function()

        # Call the function with inputs as kwargs
        import asyncio
        if asyncio.iscoroutinefunction(func):
            result = await func(**inputs)
        else:
            result = func(**inputs)

        # Ensure result is a dict
        if isinstance(result, dict):
            return result
        return {"result": result}

    async def _mock_execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Function skills typically don't need mocking - run them directly."""
        return await self._execute(inputs)

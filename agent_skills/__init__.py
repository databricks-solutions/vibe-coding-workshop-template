"""
Agent Skills Framework
======================

A dynamic, declarative framework for building agentic search and data pipelines.

Instead of hardcoding orchestration logic, skills are defined as YAML manifests
and composed into flows. This allows new business use cases to be supported by
adding configuration files rather than rewriting Python code.

Architecture Layers:
    1. Skill Registry   - Discovers and loads skill manifests
    2. Executors         - Typed runners for each skill type (LLM, Genie, etc.)
    3. Flow Engine       - Orchestrates multi-step pipelines with conditions
    4. Prompt Management - Loads prompts from Databricks Prompt Registry
    5. PRD Mapper        - Generates skills and flows from a PRD document

Usage:
    from agent_skills import SkillRegistry, FlowEngine

    registry = SkillRegistry()
    engine = FlowEngine(registry)
    result = await engine.execute_flow("assistant_search", {"message": "hotels in Miami"})
"""

from agent_skills.registry import SkillRegistry
from agent_skills.engine import FlowEngine
from agent_skills.models import SkillManifest, FlowDefinition, SkillResult

__all__ = [
    "SkillRegistry",
    "FlowEngine",
    "SkillManifest",
    "FlowDefinition",
    "SkillResult",
]

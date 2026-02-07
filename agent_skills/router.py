"""
Agent Skills - FastAPI Router Integration
===========================================

Provides a FastAPI router that exposes the flow engine as API endpoints.
This can replace or complement the existing hardcoded search router.

Endpoints:
    POST /api/skills/execute/{flow_id}   → Execute a flow
    GET  /api/skills/registry             → List all skills and flows
    GET  /api/skills/flows                → List all flows
    GET  /api/skills/flows/{flow_id}      → Get flow details
    GET  /api/skills/health               → Health check
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_skills.registry import SkillRegistry
from agent_skills.engine import FlowEngine
from agent_skills.models import SkillStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["agent-skills"])


# =============================================================================
# Singleton instances
# =============================================================================

_registry: Optional[SkillRegistry] = None
_engine: Optional[FlowEngine] = None


def get_registry() -> SkillRegistry:
    """Get or create the skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _registry.load()
    return _registry


def get_engine() -> FlowEngine:
    """Get or create the flow engine."""
    global _engine
    if _engine is None:
        _engine = FlowEngine(get_registry())
    return _engine


# =============================================================================
# Request/Response Models
# =============================================================================

class FlowExecuteRequest(BaseModel):
    """Request to execute a flow."""
    inputs: Dict[str, Any] = Field(default_factory=dict)
    mock_mode: Optional[bool] = None


class StepResultSummary(BaseModel):
    """Summary of a step execution result."""
    skill_id: str
    step_id: str
    status: str
    latency_ms: int
    error: Optional[str] = None


class FlowExecuteResponse(BaseModel):
    """Response from flow execution."""
    flow_id: str
    status: str
    response: Dict[str, Any]
    steps: List[StepResultSummary]
    total_latency_ms: int
    display: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SkillSummary(BaseModel):
    """Summary of a registered skill."""
    skill_id: str
    name: str
    type: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    version: int = 1


class FlowSummary(BaseModel):
    """Summary of a registered flow."""
    flow_id: str
    name: str
    description: Optional[str] = None
    trigger: Optional[str] = None
    step_count: int
    tags: List[str] = Field(default_factory=list)
    version: int = 1


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/execute/{flow_id}", response_model=FlowExecuteResponse)
async def execute_flow(flow_id: str, request: FlowExecuteRequest) -> FlowExecuteResponse:
    """
    Execute a flow by ID.

    Runs the full pipeline: resolves inputs, executes skills,
    evaluates conditions, and returns mapped results.
    """
    engine = get_engine()

    logger.info(f"[SkillsRouter] Executing flow: {flow_id}")

    result = await engine.execute_flow(
        flow_id=flow_id,
        request=request.inputs,
        mock_mode=request.mock_mode,
    )

    # Build step summaries
    step_summaries = [
        StepResultSummary(
            skill_id=sr.skill_id,
            step_id=sr.step_id,
            status=sr.status.value,
            latency_ms=sr.latency_ms,
            error=sr.error,
        )
        for sr in result.step_results.values()
    ]

    return FlowExecuteResponse(
        flow_id=result.flow_id,
        status=result.status.value,
        response=result.response,
        steps=step_summaries,
        total_latency_ms=result.total_latency_ms,
        display=result.display.model_dump() if result.display else None,
        error=result.error,
    )


@router.get("/registry")
async def get_registry_info():
    """List all registered skills and flows."""
    registry = get_registry()

    return {
        "skills": [
            SkillSummary(
                skill_id=s.skill_id,
                name=s.name,
                type=s.type.value,
                description=s.description,
                tags=s.tags,
                version=s.version,
            ).model_dump()
            for s in registry.list_skills()
        ],
        "flows": [
            FlowSummary(
                flow_id=f.flow_id,
                name=f.name,
                description=f.description,
                trigger=f.trigger,
                step_count=len(f.steps),
                tags=f.tags,
                version=f.version,
            ).model_dump()
            for f in registry.list_flows()
        ],
        "config": {
            "version": registry.config.version,
            "description": registry.config.description,
            "default_flow": registry.config.default_flow,
        },
    }


@router.get("/flows")
async def list_flows():
    """List all registered flows."""
    registry = get_registry()
    return {
        "flows": [
            {
                "flow_id": f.flow_id,
                "name": f.name,
                "description": f.description,
                "trigger": f.trigger,
                "steps": [
                    {"id": s.id, "skill": s.skill, "condition": s.condition}
                    for s in f.steps
                ],
                "display": f.display.model_dump() if f.display else None,
                "tags": f.tags,
            }
            for f in registry.list_flows()
        ]
    }


@router.get("/flows/{flow_id}")
async def get_flow_detail(flow_id: str):
    """Get detailed information about a specific flow."""
    registry = get_registry()
    flow = registry.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")

    return {
        "flow_id": flow.flow_id,
        "name": flow.name,
        "description": flow.description,
        "trigger": flow.trigger,
        "version": flow.version,
        "steps": [
            {
                "id": s.id,
                "skill": s.skill,
                "inputs": [
                    {"field": inp.field, "reference": inp.reference, "value": inp.value}
                    for inp in s.inputs
                ],
                "condition": s.condition,
            }
            for s in flow.steps
        ],
        "response_mappings": [
            {"field": r.field, "reference": r.reference, "default": r.default}
            for r in flow.response
        ],
        "display": flow.display.model_dump() if flow.display else None,
        "tags": flow.tags,
    }


@router.get("/health")
async def skills_health():
    """Health check for the agent skills framework."""
    try:
        registry = get_registry()
        return {
            "status": "ok",
            "skills_loaded": len(registry.list_skills()),
            "flows_loaded": len(registry.list_flows()),
            "default_flow": registry.config.default_flow,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

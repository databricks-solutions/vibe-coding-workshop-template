"""
Agent Skills - Core Models
==========================

Pydantic models that define the schema for skills, flows, and execution results.
These models are the contract between all layers of the framework.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class SkillType(str, Enum):
    """Supported skill executor types."""
    LLM_CALL = "llm_call"
    GENIE_QUERY = "genie_query"
    WEB_SEARCH = "web_search"
    LAKEBASE_QUERY = "lakebase_query"
    FUNCTION = "function"
    PROMPT_REGISTRY = "prompt_registry"


class SkillStatus(str, Enum):
    """Execution status of a skill."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    NO_DATA = "no_data"


class FallbackStrategy(str, Enum):
    """What to do when a skill fails."""
    PASSTHROUGH = "passthrough"    # Use an input field as the output
    DEFAULT_VALUE = "default_value"  # Return a static default
    SKIP = "skip"                  # Mark as skipped, continue flow


class PromptSource(str, Enum):
    """Where to load the system prompt from."""
    INLINE = "inline"              # Defined directly in the manifest
    REGISTRY = "registry"          # Databricks Prompt Registry URI
    FILE = "file"                  # Local file path


# =============================================================================
# Skill Manifest
# =============================================================================

class FallbackConfig(BaseModel):
    """Configuration for skill failure handling."""
    strategy: FallbackStrategy = FallbackStrategy.SKIP
    passthrough_field: Optional[str] = None
    default_value: Optional[Any] = None


class PromptConfig(BaseModel):
    """Configuration for prompt loading."""
    source: PromptSource = PromptSource.INLINE
    inline_text: Optional[str] = None
    registry_uri: Optional[str] = None
    file_path: Optional[str] = None
    version: Optional[int] = None


class SkillConfig(BaseModel):
    """Provider-specific configuration for a skill."""
    endpoint: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    space_id: Optional[str] = None
    provider: Optional[str] = None
    api_key_env: Optional[str] = None
    # For function-type skills
    module_path: Optional[str] = None
    function_name: Optional[str] = None
    # For prompt registry skills
    prompt: Optional[PromptConfig] = None
    # Arbitrary extra config
    extra: Dict[str, Any] = Field(default_factory=dict)


class FieldSchema(BaseModel):
    """Schema definition for an input or output field."""
    name: str
    type: str = "string"  # string, number, boolean, list, object
    required: bool = True
    description: Optional[str] = None
    default: Optional[Any] = None


class SkillManifest(BaseModel):
    """
    Declarative definition of a single agent skill.

    A skill is a unit of work (LLM call, database query, API call, etc.)
    that can be composed into flows.
    """
    skill_id: str
    name: str
    description: Optional[str] = None
    version: int = 1
    type: SkillType
    config: SkillConfig = Field(default_factory=SkillConfig)
    input_schema: List[FieldSchema] = Field(default_factory=list)
    output_schema: List[FieldSchema] = Field(default_factory=list)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    tags: List[str] = Field(default_factory=list)
    mock_enabled: bool = True


# =============================================================================
# Flow Definition
# =============================================================================

class StepInput(BaseModel):
    """
    Mapping of input field name to a value or variable reference.

    Variable references use ${step_id.output.field_name} or ${request.field_name}.
    """
    field: str
    value: Optional[Any] = None         # Static value
    reference: Optional[str] = None     # Dynamic reference: ${step.output.field}


class FlowStep(BaseModel):
    """A single step in a flow pipeline."""
    skill: str                         # skill_id from registry
    id: str                            # Unique step ID within the flow
    inputs: List[StepInput] = Field(default_factory=list)
    condition: Optional[str] = None    # Python-like condition expression
    parallel_with: Optional[List[str]] = None  # Step IDs to run in parallel with


class ResponseMapping(BaseModel):
    """Maps a response field to a step output or expression."""
    field: str
    reference: Optional[str] = None
    default: Optional[Any] = None


class DisplayConfig(BaseModel):
    """Frontend display configuration for a flow's results."""
    type: str = "inline"  # inline, page, modal, toast
    show_answer: bool = True
    results_format: str = "cards"  # cards, list, table
    show_sources: bool = True
    show_rewritten_query: bool = True
    show_follow_up: bool = False


class FlowDefinition(BaseModel):
    """
    Declarative definition of a multi-step agent pipeline.

    Flows chain skills together with conditional logic, variable passing,
    and response mapping.
    """
    flow_id: str
    name: str
    description: Optional[str] = None
    version: int = 1
    trigger: Optional[str] = None  # e.g., "POST /api/search/assistant"
    steps: List[FlowStep] = Field(default_factory=list)
    response: List[ResponseMapping] = Field(default_factory=list)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    tags: List[str] = Field(default_factory=list)


# =============================================================================
# Execution Results
# =============================================================================

class SkillResult(BaseModel):
    """Result of executing a single skill."""
    skill_id: str
    step_id: str
    status: SkillStatus
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == SkillStatus.SUCCESS


class FlowResult(BaseModel):
    """Result of executing a complete flow."""
    flow_id: str
    status: SkillStatus
    response: Dict[str, Any] = Field(default_factory=dict)
    step_results: Dict[str, SkillResult] = Field(default_factory=dict)
    total_latency_ms: int = 0
    display: Optional[DisplayConfig] = None
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == SkillStatus.SUCCESS


# =============================================================================
# Registry Config
# =============================================================================

class RegistryConfig(BaseModel):
    """Top-level registry configuration."""
    version: int = 1
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)       # Skill folder names
    flows: List[str] = Field(default_factory=list)         # Flow file names
    default_flow: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

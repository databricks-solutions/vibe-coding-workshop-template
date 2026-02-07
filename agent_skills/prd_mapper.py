"""
Agent Skills - PRD-to-Skills Mapper
=====================================

Analyzes a Product Requirements Document and generates skill manifests
and flow definitions to support the described use case.

This mapper uses an LLM to understand the PRD and produce:
1. Skill manifests for each capability (search, recommend, etc.)
2. Flow definitions for each user journey
3. Configuration stubs for required services

Usage:
    mapper = PRDMapper()
    skills, flows = await mapper.generate_from_prd("docs/design_prd.md")
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from agent_skills.models import (
    DisplayConfig,
    FallbackConfig,
    FallbackStrategy,
    FieldSchema,
    FlowDefinition,
    FlowStep,
    PromptConfig,
    PromptSource,
    ResponseMapping,
    SkillConfig,
    SkillManifest,
    SkillType,
    StepInput,
)

logger = logging.getLogger(__name__)


# System prompt for the PRD analysis LLM call
PRD_ANALYSIS_PROMPT = """You are an agent framework architect. Given a Product Requirements Document (PRD), 
analyze it and produce a JSON specification for the skills and flows needed.

For each distinct capability needed by the application, define a skill.
For each user journey in the PRD, define a flow that chains skills together.

Respond ONLY with valid JSON in this format:
{
    "skills": [
        {
            "skill_id": "unique_identifier",
            "name": "Human-readable name",
            "description": "What this skill does",
            "type": "llm_call|genie_query|web_search|lakebase_query|function",
            "inputs": [{"name": "field_name", "type": "string", "required": true}],
            "outputs": [{"name": "field_name", "type": "string"}],
            "tags": ["category"]
        }
    ],
    "flows": [
        {
            "flow_id": "unique_identifier",
            "name": "Human-readable name",
            "description": "What this flow does",
            "trigger": "HTTP trigger or event",
            "steps": [
                {
                    "skill": "skill_id",
                    "id": "step_id",
                    "inputs": {"field": "value_or_reference"},
                    "condition": "optional condition"
                }
            ],
            "display_type": "inline|page|modal"
        }
    ]
}

Focus on:
- Search and discovery capabilities
- Natural language processing needs
- Database query requirements
- External data integration points
- User journey orchestration
"""


class PRDMapper:
    """
    Generates agent skill manifests and flow definitions from a PRD.

    Can operate in two modes:
    1. LLM-powered: Sends PRD to a Databricks LLM endpoint for analysis
    2. Template-based: Uses heuristic rules to generate common patterns
    """

    def __init__(self, llm_endpoint: Optional[str] = None):
        """
        Initialize the mapper.

        Args:
            llm_endpoint: Databricks model serving endpoint name. If None,
                         uses template-based generation.
        """
        self.llm_endpoint = llm_endpoint or os.getenv("LLM_ENDPOINT_NAME", "")
        self._workspace_client = None

    async def generate_from_prd(
        self,
        prd_path: str,
        output_dir: Optional[str] = None,
        use_llm: bool = False,
    ) -> Tuple[List[SkillManifest], List[FlowDefinition]]:
        """
        Generate skills and flows from a PRD file.

        Args:
            prd_path: Path to the PRD markdown file.
            output_dir: Optional directory to write generated YAML files.
            use_llm: Whether to use LLM analysis (vs template-based).

        Returns:
            Tuple of (skills, flows).
        """
        logger.info(f"[PRDMapper] Analyzing PRD: {prd_path}")

        # Read the PRD
        prd_content = self._read_prd(prd_path)
        if not prd_content:
            logger.error(f"[PRDMapper] Could not read PRD: {prd_path}")
            return [], []

        # Generate skills and flows
        if use_llm and self.llm_endpoint:
            skills, flows = await self._generate_with_llm(prd_content)
        else:
            skills, flows = self._generate_with_templates(prd_content)

        logger.info(
            f"[PRDMapper] Generated {len(skills)} skills, {len(flows)} flows"
        )

        # Write to disk if output_dir specified
        if output_dir:
            self._write_to_disk(skills, flows, output_dir)

        return skills, flows

    # =========================================================================
    # PRD Reading
    # =========================================================================

    def _read_prd(self, prd_path: str) -> Optional[str]:
        """Read a PRD file."""
        try:
            path = Path(prd_path)
            if not path.exists():
                # Try relative to workspace
                workspace = Path(os.getenv("WORKSPACE_PATH", "."))
                path = workspace / prd_path
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[PRDMapper] Failed to read PRD: {e}")
            return None

    # =========================================================================
    # LLM-Powered Generation
    # =========================================================================

    async def _generate_with_llm(
        self, prd_content: str
    ) -> Tuple[List[SkillManifest], List[FlowDefinition]]:
        """Use an LLM to analyze the PRD and generate specs."""
        try:
            ws = self._get_workspace_client()

            response = ws.serving_endpoints.query(
                name=self.llm_endpoint,
                messages=[
                    {"role": "system", "content": PRD_ANALYSIS_PROMPT},
                    {"role": "user", "content": f"Analyze this PRD:\n\n{prd_content[:8000]}"},
                ],
                temperature=0.2,
                max_tokens=4096,
            )

            response_text = response.choices[0].message.content

            # Parse JSON
            data = self._parse_json(response_text)
            if not data:
                logger.warning("[PRDMapper] LLM returned invalid JSON, falling back to templates")
                return self._generate_with_templates(prd_content)

            skills = self._build_skills_from_spec(data.get("skills", []))
            flows = self._build_flows_from_spec(data.get("flows", []))

            return skills, flows

        except Exception as e:
            logger.error(f"[PRDMapper] LLM generation failed: {e}")
            return self._generate_with_templates(prd_content)

    def _get_workspace_client(self):
        if self._workspace_client is None:
            from databricks.sdk import WorkspaceClient
            self._workspace_client = WorkspaceClient()
        return self._workspace_client

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    # =========================================================================
    # Template-Based Generation
    # =========================================================================

    def _generate_with_templates(
        self, prd_content: str
    ) -> Tuple[List[SkillManifest], List[FlowDefinition]]:
        """
        Use heuristic rules to generate common skill/flow patterns.

        Analyzes the PRD for keywords and patterns to determine which
        standard templates to apply.
        """
        prd_lower = prd_content.lower()
        skills: List[SkillManifest] = []
        flows: List[FlowDefinition] = []

        # Detect features from PRD keywords
        has_search = any(w in prd_lower for w in ["search", "discover", "find", "browse"])
        has_nlp = any(w in prd_lower for w in ["natural language", "ai-powered", "agent", "assistant"])
        has_booking = any(w in prd_lower for w in ["booking", "reservation", "checkout", "purchase"])
        has_reviews = any(w in prd_lower for w in ["review", "rating", "feedback"])
        has_recommendations = any(w in prd_lower for w in ["recommend", "suggest", "personalize"])

        logger.info(
            f"[PRDMapper] Detected features: search={has_search}, nlp={has_nlp}, "
            f"booking={has_booking}, reviews={has_reviews}, recommendations={has_recommendations}"
        )

        # Generate skills based on detected features
        if has_search:
            skills.append(self._template_lakebase_search())

        if has_nlp:
            skills.append(self._template_query_rewriter())
            skills.append(self._template_genie_search())
            skills.append(self._template_web_search())
            skills.append(self._template_web_summarizer())
            skills.append(self._template_location_extractor())

        if has_booking:
            skills.append(self._template_booking_processor())

        if has_reviews:
            skills.append(self._template_review_fetcher())

        if has_recommendations:
            skills.append(self._template_recommendation_engine())

        # Generate flows
        if has_search:
            flows.append(self._template_standard_search_flow())

        if has_nlp:
            flows.append(self._template_assistant_search_flow())

        if has_booking:
            flows.append(self._template_booking_flow())

        return skills, flows

    # =========================================================================
    # Skill Templates
    # =========================================================================

    def _template_query_rewriter(self) -> SkillManifest:
        return SkillManifest(
            skill_id="query_rewriter",
            name="Query Rewriter",
            description="Rewrites natural language queries for structured search",
            type=SkillType.LLM_CALL,
            config=SkillConfig(
                endpoint="${LLM_ENDPOINT_URL}",
                temperature=0.2,
                max_tokens=1024,
                prompt=PromptConfig(source=PromptSource.INLINE, inline_text="..."),
            ),
            input_schema=[
                FieldSchema(name="user_query", type="string", required=True),
                FieldSchema(name="preferences", type="object", required=False),
            ],
            output_schema=[
                FieldSchema(name="rewritten_query", type="string"),
                FieldSchema(name="assumptions", type="list"),
            ],
            fallback=FallbackConfig(strategy=FallbackStrategy.PASSTHROUGH, passthrough_field="user_query"),
            tags=["search", "nlp"],
        )

    def _template_genie_search(self) -> SkillManifest:
        return SkillManifest(
            skill_id="genie_search",
            name="Genie Space Search",
            description="Queries Genie Space for natural language results",
            type=SkillType.GENIE_QUERY,
            config=SkillConfig(space_id="${GENIE_SPACE_ID}", timeout_seconds=60),
            input_schema=[FieldSchema(name="query_text", type="string", required=True)],
            output_schema=[
                FieldSchema(name="answer_text", type="string"),
                FieldSchema(name="items", type="list"),
                FieldSchema(name="genie_status", type="string"),
            ],
            fallback=FallbackConfig(strategy=FallbackStrategy.SKIP),
            tags=["search", "genie"],
        )

    def _template_web_search(self) -> SkillManifest:
        return SkillManifest(
            skill_id="web_search",
            name="Web Search Fallback",
            description="Web search when internal sources fail",
            type=SkillType.WEB_SEARCH,
            config=SkillConfig(provider="${WEB_SEARCH_PROVIDER}", api_key_env="WEB_SEARCH_API_KEY"),
            input_schema=[FieldSchema(name="query", type="string", required=True)],
            output_schema=[
                FieldSchema(name="snippets", type="list"),
                FieldSchema(name="links", type="list"),
                FieldSchema(name="search_status", type="string"),
            ],
            fallback=FallbackConfig(strategy=FallbackStrategy.DEFAULT_VALUE, default_value={"snippets": [], "links": [], "search_status": "no_config"}),
            tags=["search", "fallback"],
        )

    def _template_web_summarizer(self) -> SkillManifest:
        return SkillManifest(
            skill_id="web_result_summarizer",
            name="Web Result Summarizer",
            description="Summarizes web search results into recommendations",
            type=SkillType.LLM_CALL,
            config=SkillConfig(endpoint="${LLM_ENDPOINT_URL}", temperature=0.3),
            input_schema=[
                FieldSchema(name="snippets", type="list", required=True),
                FieldSchema(name="user_query", type="string", required=True),
            ],
            output_schema=[
                FieldSchema(name="summary", type="string"),
                FieldSchema(name="suggestions", type="list"),
            ],
            tags=["search", "llm"],
        )

    def _template_lakebase_search(self) -> SkillManifest:
        return SkillManifest(
            skill_id="lakebase_search",
            name="Lakebase Database Search",
            description="Searches PostgreSQL database for listings",
            type=SkillType.LAKEBASE_QUERY,
            config=SkillConfig(extra={"query_type": "search_listings"}),
            input_schema=[
                FieldSchema(name="location", type="string", required=True),
                FieldSchema(name="guests", type="number", required=False, default=2),
            ],
            output_schema=[
                FieldSchema(name="items", type="list"),
                FieldSchema(name="total_count", type="number"),
            ],
            tags=["search", "database"],
        )

    def _template_location_extractor(self) -> SkillManifest:
        return SkillManifest(
            skill_id="location_extractor",
            name="Location Extractor",
            description="Extracts location from query text",
            type=SkillType.FUNCTION,
            config=SkillConfig(
                module_path="agent_skills.executors.function_executor",
                function_name="extract_location_hint",
            ),
            input_schema=[FieldSchema(name="query_text", type="string", required=True)],
            output_schema=[FieldSchema(name="location", type="string")],
            tags=["utility"],
            mock_enabled=False,
        )

    def _template_booking_processor(self) -> SkillManifest:
        return SkillManifest(
            skill_id="booking_processor",
            name="Booking Processor",
            description="Processes a booking request and creates reservation",
            type=SkillType.LAKEBASE_QUERY,
            config=SkillConfig(extra={"query_type": "create_booking"}),
            input_schema=[
                FieldSchema(name="listing_id", type="string", required=True),
                FieldSchema(name="check_in", type="string", required=True),
                FieldSchema(name="check_out", type="string", required=True),
                FieldSchema(name="guests", type="number", required=True),
                FieldSchema(name="guest_name", type="string", required=True),
                FieldSchema(name="guest_email", type="string", required=True),
            ],
            output_schema=[
                FieldSchema(name="booking_ref", type="string"),
                FieldSchema(name="success", type="boolean"),
            ],
            tags=["booking", "transaction"],
        )

    def _template_review_fetcher(self) -> SkillManifest:
        return SkillManifest(
            skill_id="review_fetcher",
            name="Review Fetcher",
            description="Fetches reviews for a listing",
            type=SkillType.LAKEBASE_QUERY,
            config=SkillConfig(extra={"query_type": "get_reviews"}),
            input_schema=[FieldSchema(name="listing_id", type="string", required=True)],
            output_schema=[
                FieldSchema(name="reviews", type="list"),
                FieldSchema(name="total_count", type="number"),
            ],
            tags=["reviews", "content"],
        )

    def _template_recommendation_engine(self) -> SkillManifest:
        return SkillManifest(
            skill_id="recommendation_engine",
            name="Recommendation Engine",
            description="Generates personalized recommendations using LLM",
            type=SkillType.LLM_CALL,
            config=SkillConfig(endpoint="${LLM_ENDPOINT_URL}"),
            input_schema=[
                FieldSchema(name="user_preferences", type="object", required=True),
                FieldSchema(name="available_listings", type="list", required=True),
            ],
            output_schema=[
                FieldSchema(name="recommendations", type="list"),
                FieldSchema(name="reasoning", type="string"),
            ],
            tags=["recommendation", "llm"],
        )

    # =========================================================================
    # Flow Templates
    # =========================================================================

    def _template_standard_search_flow(self) -> FlowDefinition:
        return FlowDefinition(
            flow_id="standard_search",
            name="Standard Search",
            description="Structured search with location and filters",
            trigger="POST /api/search/standard",
            steps=[
                FlowStep(
                    skill="lakebase_search",
                    id="search",
                    inputs=[
                        StepInput(field="location", reference="${request.location}"),
                        StepInput(field="guests", reference="${request.guests}"),
                    ],
                ),
            ],
            response=[
                ResponseMapping(field="results", reference="${search.output.items}"),
                ResponseMapping(field="totalResults", reference="${search.output.total_count}"),
            ],
            display=DisplayConfig(type="page", show_answer=False, show_sources=False),
            tags=["search", "standard"],
        )

    def _template_assistant_search_flow(self) -> FlowDefinition:
        return FlowDefinition(
            flow_id="assistant_search",
            name="Assistant Search",
            description="NL search with LLM, Genie, and web fallback",
            trigger="POST /api/search/assistant",
            steps=[
                FlowStep(
                    skill="query_rewriter",
                    id="rewrite",
                    inputs=[
                        StepInput(field="user_query", reference="${request.message}"),
                        StepInput(field="preferences", reference="${request.preferences}"),
                    ],
                ),
                FlowStep(
                    skill="genie_search",
                    id="genie",
                    inputs=[
                        StepInput(field="query_text", reference="${rewrite.output.rewritten_query}"),
                    ],
                ),
                FlowStep(
                    skill="web_search",
                    id="web_fallback",
                    condition='${genie.output.genie_status} != "ok"',
                    inputs=[
                        StepInput(field="query", reference="${rewrite.output.rewritten_query}"),
                    ],
                ),
                FlowStep(
                    skill="web_result_summarizer",
                    id="summarize",
                    condition='${web_fallback.output.search_status} == "ok"',
                    inputs=[
                        StepInput(field="snippets", reference="${web_fallback.output.snippets}"),
                        StepInput(field="user_query", reference="${request.message}"),
                    ],
                ),
            ],
            response=[
                ResponseMapping(field="rewrittenQuery", reference="${rewrite.output.rewritten_query}"),
                ResponseMapping(field="answer", reference="${genie.output.answer_text}"),
            ],
            display=DisplayConfig(type="inline", show_answer=True, show_sources=True),
            tags=["search", "assistant"],
        )

    def _template_booking_flow(self) -> FlowDefinition:
        return FlowDefinition(
            flow_id="create_booking",
            name="Create Booking",
            description="Process a booking request",
            trigger="POST /api/bookings",
            steps=[
                FlowStep(
                    skill="booking_processor",
                    id="process_booking",
                    inputs=[
                        StepInput(field="listing_id", reference="${request.listingId}"),
                        StepInput(field="check_in", reference="${request.checkIn}"),
                        StepInput(field="check_out", reference="${request.checkOut}"),
                        StepInput(field="guests", reference="${request.guests}"),
                        StepInput(field="guest_name", reference="${request.guestName}"),
                        StepInput(field="guest_email", reference="${request.guestEmail}"),
                    ],
                ),
            ],
            response=[
                ResponseMapping(field="bookingRef", reference="${process_booking.output.booking_ref}"),
                ResponseMapping(field="success", reference="${process_booking.output.success}"),
            ],
            display=DisplayConfig(type="page"),
            tags=["booking"],
        )

    # =========================================================================
    # LLM Spec → Model Conversion
    # =========================================================================

    def _build_skills_from_spec(self, specs: List[Dict]) -> List[SkillManifest]:
        """Convert LLM-generated specs to SkillManifest objects."""
        skills = []
        type_map = {
            "llm_call": SkillType.LLM_CALL,
            "genie_query": SkillType.GENIE_QUERY,
            "web_search": SkillType.WEB_SEARCH,
            "lakebase_query": SkillType.LAKEBASE_QUERY,
            "function": SkillType.FUNCTION,
        }

        for spec in specs:
            try:
                skill_type = type_map.get(spec.get("type", ""), SkillType.FUNCTION)
                skills.append(SkillManifest(
                    skill_id=spec["skill_id"],
                    name=spec["name"],
                    description=spec.get("description", ""),
                    type=skill_type,
                    input_schema=[FieldSchema(**f) for f in spec.get("inputs", [])],
                    output_schema=[FieldSchema(**f) for f in spec.get("outputs", [])],
                    tags=spec.get("tags", []),
                ))
            except Exception as e:
                logger.warning(f"[PRDMapper] Failed to build skill from spec: {e}")

        return skills

    def _build_flows_from_spec(self, specs: List[Dict]) -> List[FlowDefinition]:
        """Convert LLM-generated specs to FlowDefinition objects."""
        flows = []
        for spec in specs:
            try:
                steps = []
                for step_spec in spec.get("steps", []):
                    inputs = []
                    for field, value in step_spec.get("inputs", {}).items():
                        if isinstance(value, str) and value.startswith("${"):
                            inputs.append(StepInput(field=field, reference=value))
                        else:
                            inputs.append(StepInput(field=field, value=value))

                    steps.append(FlowStep(
                        skill=step_spec["skill"],
                        id=step_spec["id"],
                        inputs=inputs,
                        condition=step_spec.get("condition"),
                    ))

                display_type = spec.get("display_type", "inline")
                flows.append(FlowDefinition(
                    flow_id=spec["flow_id"],
                    name=spec["name"],
                    description=spec.get("description", ""),
                    trigger=spec.get("trigger"),
                    steps=steps,
                    display=DisplayConfig(type=display_type),
                    tags=spec.get("tags", []),
                ))
            except Exception as e:
                logger.warning(f"[PRDMapper] Failed to build flow from spec: {e}")

        return flows

    # =========================================================================
    # Disk Output
    # =========================================================================

    def _write_to_disk(
        self,
        skills: List[SkillManifest],
        flows: List[FlowDefinition],
        output_dir: str,
    ) -> None:
        """Write generated skills and flows to YAML files."""
        output_path = Path(output_dir)

        # Write skills
        skills_dir = output_path / "skills"
        for skill in skills:
            skill_dir = skills_dir / skill.skill_id
            skill_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = skill_dir / "manifest.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(
                    skill.model_dump(exclude_none=True),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.info(f"[PRDMapper] Wrote skill: {manifest_path}")

        # Write flows
        flows_dir = output_path / "flows"
        flows_dir.mkdir(parents=True, exist_ok=True)
        for flow in flows:
            flow_path = flows_dir / f"{flow.flow_id}.yaml"
            with open(flow_path, "w") as f:
                yaml.dump(
                    flow.model_dump(exclude_none=True),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.info(f"[PRDMapper] Wrote flow: {flow_path}")

        logger.info(f"[PRDMapper] Generated artifacts saved to {output_dir}")

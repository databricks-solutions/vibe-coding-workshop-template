"""
Tests for SkillRegistry
========================

Verifies skill and flow loading, lookup, and registration.
"""

import os
import pytest
from pathlib import Path

from agent_skills.registry import SkillRegistry
from agent_skills.models import SkillManifest, SkillType, FlowDefinition


@pytest.fixture
def registry():
    """Create a registry pointing at the real skills directory."""
    base_dir = Path(__file__).parent.parent
    reg = SkillRegistry(base_dir=str(base_dir))
    reg.load()
    return reg


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_registry_loads_skills(self, registry):
        """Registry should load all skill manifests."""
        skills = registry.list_skills()
        assert len(skills) >= 6, f"Expected at least 6 skills, got {len(skills)}"

    def test_registry_loads_flows(self, registry):
        """Registry should load all flow definitions."""
        flows = registry.list_flows()
        assert len(flows) >= 2, f"Expected at least 2 flows, got {len(flows)}"

    def test_get_skill_by_id(self, registry):
        """Should retrieve a skill by its ID."""
        skill = registry.get_skill("query_rewriter")
        assert skill is not None
        assert skill.name == "Query Rewriter"
        assert skill.type == SkillType.LLM_CALL

    def test_get_nonexistent_skill(self, registry):
        """Should return None for unknown skill IDs."""
        skill = registry.get_skill("nonexistent_skill")
        assert skill is None

    def test_get_flow_by_id(self, registry):
        """Should retrieve a flow by its ID."""
        flow = registry.get_flow("assistant_search")
        assert flow is not None
        assert flow.name == "Assistant Search"
        assert len(flow.steps) >= 4

    def test_get_skills_by_tag(self, registry):
        """Should filter skills by tag."""
        search_skills = registry.get_skills_by_tag("search")
        assert len(search_skills) >= 3

    def test_programmatic_registration(self, registry):
        """Should allow programmatic skill registration."""
        custom = SkillManifest(
            skill_id="custom_test_skill",
            name="Custom Test",
            type=SkillType.FUNCTION,
        )
        registry.register_skill(custom)
        retrieved = registry.get_skill("custom_test_skill")
        assert retrieved is not None
        assert retrieved.name == "Custom Test"

    def test_skill_manifest_validation(self, registry):
        """All loaded skills should have required fields."""
        for skill in registry.list_skills():
            assert skill.skill_id, "skill_id is required"
            assert skill.name, "name is required"
            assert skill.type, "type is required"

    def test_flow_steps_reference_valid_skills(self, registry):
        """All flow steps should reference skills that exist."""
        for flow in registry.list_flows():
            for step in flow.steps:
                skill = registry.get_skill(step.skill)
                assert skill is not None, (
                    f"Flow '{flow.flow_id}' step '{step.id}' references "
                    f"unknown skill '{step.skill}'"
                )

    def test_assistant_flow_structure(self, registry):
        """The assistant_search flow should have the expected structure."""
        flow = registry.get_flow("assistant_search")
        assert flow is not None

        step_ids = [s.id for s in flow.steps]
        assert "rewrite" in step_ids
        assert "genie" in step_ids
        assert "web_fallback" in step_ids

        # Web fallback should have a condition
        web_step = next(s for s in flow.steps if s.id == "web_fallback")
        assert web_step.condition is not None

    def test_flow_display_config(self, registry):
        """Flows should have display configuration."""
        flow = registry.get_flow("assistant_search")
        assert flow.display is not None
        assert flow.display.type == "inline"
        assert flow.display.show_answer is True

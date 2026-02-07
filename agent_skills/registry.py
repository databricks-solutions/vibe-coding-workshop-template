"""
Agent Skills - Skill Registry
==============================

Discovers, loads, and manages skill manifests and flow definitions from YAML files.
Acts as the central lookup table for the flow engine.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agent_skills.models import (
    FlowDefinition,
    RegistryConfig,
    SkillManifest,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Central registry for agent skills and flows.

    Loads skill manifests and flow definitions from a directory structure:

        agent_skills/
            skill_registry.yaml         ← master config
            skills/
                query_rewriter/
                    manifest.yaml
                genie_search/
                    manifest.yaml
            flows/
                assistant_search.yaml
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the registry.

        Args:
            base_dir: Root directory of agent_skills. Defaults to this package's dir.
        """
        self.base_dir = Path(base_dir or os.path.dirname(__file__))
        self.skills_dir = self.base_dir / "skills"
        self.flows_dir = self.base_dir / "flows"

        self._skills: Dict[str, SkillManifest] = {}
        self._flows: Dict[str, FlowDefinition] = {}
        self._config: Optional[RegistryConfig] = None

        self._loaded = False

    # =========================================================================
    # Public API
    # =========================================================================

    def load(self) -> None:
        """Load all skills and flows from disk."""
        logger.info(f"[SkillRegistry] Loading from {self.base_dir}")

        # Load master config
        config_path = self.base_dir / "skill_registry.yaml"
        if config_path.exists():
            self._config = self._load_registry_config(config_path)
            logger.info(f"[SkillRegistry] Registry config loaded: {self._config.description}")
        else:
            self._config = RegistryConfig()
            logger.warning("[SkillRegistry] No skill_registry.yaml found, using defaults")

        # Load skills
        self._load_all_skills()

        # Load flows
        self._load_all_flows()

        self._loaded = True
        logger.info(
            f"[SkillRegistry] Loaded {len(self._skills)} skills, {len(self._flows)} flows"
        )

    def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """Get a skill manifest by ID."""
        self._ensure_loaded()
        return self._skills.get(skill_id)

    def get_flow(self, flow_id: str) -> Optional[FlowDefinition]:
        """Get a flow definition by ID."""
        self._ensure_loaded()
        return self._flows.get(flow_id)

    def list_skills(self) -> List[SkillManifest]:
        """List all registered skills."""
        self._ensure_loaded()
        return list(self._skills.values())

    def list_flows(self) -> List[FlowDefinition]:
        """List all registered flows."""
        self._ensure_loaded()
        return list(self._flows.values())

    def get_skills_by_tag(self, tag: str) -> List[SkillManifest]:
        """Get all skills with a given tag."""
        self._ensure_loaded()
        return [s for s in self._skills.values() if tag in s.tags]

    def get_flows_by_tag(self, tag: str) -> List[FlowDefinition]:
        """Get all flows with a given tag."""
        self._ensure_loaded()
        return [f for f in self._flows.values() if tag in f.tags]

    def register_skill(self, manifest: SkillManifest) -> None:
        """Programmatically register a skill (e.g., from PRD generator)."""
        self._skills[manifest.skill_id] = manifest
        logger.info(f"[SkillRegistry] Registered skill: {manifest.skill_id}")

    def register_flow(self, flow: FlowDefinition) -> None:
        """Programmatically register a flow."""
        self._flows[flow.flow_id] = flow
        logger.info(f"[SkillRegistry] Registered flow: {flow.flow_id}")

    @property
    def config(self) -> RegistryConfig:
        """Get the registry configuration."""
        self._ensure_loaded()
        return self._config or RegistryConfig()

    # =========================================================================
    # Internal Loading
    # =========================================================================

    def _ensure_loaded(self) -> None:
        """Lazy-load if not already loaded."""
        if not self._loaded:
            self.load()

    def _load_registry_config(self, path: Path) -> RegistryConfig:
        """Load the master registry config."""
        data = self._read_yaml(path)
        return RegistryConfig(**data) if data else RegistryConfig()

    def _load_all_skills(self) -> None:
        """Load all skill manifests from the skills directory."""
        if not self.skills_dir.exists():
            logger.warning(f"[SkillRegistry] Skills directory not found: {self.skills_dir}")
            return

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            manifest_path = skill_dir / "manifest.yaml"
            if manifest_path.exists():
                self._load_skill(manifest_path)

    def _load_skill(self, manifest_path: Path) -> None:
        """Load a single skill manifest."""
        try:
            data = self._read_yaml(manifest_path)
            if not data:
                return
            manifest = SkillManifest(**data)
            self._skills[manifest.skill_id] = manifest
            logger.info(f"[SkillRegistry]   Skill loaded: {manifest.skill_id} (v{manifest.version})")
        except Exception as e:
            logger.error(f"[SkillRegistry] Failed to load skill from {manifest_path}: {e}")

    def _load_all_flows(self) -> None:
        """Load all flow definitions from the flows directory."""
        if not self.flows_dir.exists():
            logger.warning(f"[SkillRegistry] Flows directory not found: {self.flows_dir}")
            return

        for flow_file in sorted(self.flows_dir.glob("*.yaml")):
            self._load_flow(flow_file)

    def _load_flow(self, flow_path: Path) -> None:
        """Load a single flow definition."""
        try:
            data = self._read_yaml(flow_path)
            if not data:
                return
            flow = FlowDefinition(**data)
            self._flows[flow.flow_id] = flow
            logger.info(f"[SkillRegistry]   Flow loaded: {flow.flow_id} (v{flow.version})")
        except Exception as e:
            logger.error(f"[SkillRegistry] Failed to load flow from {flow_path}: {e}")

    @staticmethod
    def _read_yaml(path: Path) -> Optional[dict]:
        """Read and parse a YAML file."""
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"[SkillRegistry] Failed to read YAML {path}: {e}")
            return None

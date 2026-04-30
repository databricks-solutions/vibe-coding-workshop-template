#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "apps_lakebase" / "prompts"
SECTIONS = PROMPTS / "sections"
SQL = PROMPTS / "02_seed_section_input_prompts.sql"

EXPECTED_ORDER = [
    ("agent_spec_design", 38),
    ("agent_tool_selection", 39),
    ("uc_resources_foundation", 40),
    ("mlflow_agent_tracing_uc", 41),
    ("knowledge_assistant_create", 42),
    ("track_a_agent_app_clone_framework", 43),
    ("track_a_agent_ka_genie_tools", 44),
    ("track_a_agent_auth_memory", 45),
    ("track_a_agent_eval_deploy", 46),
    ("appkit_agent_app_proxy_chat", 47),
    ("appkit_chat_feedback_mlflow", 48),
]

LEGACY_FILES = [
    SECTIONS / "16-agent_framework.md",
    SECTIONS / "17-wire_ui_agent.md",
]


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path.relative_to(ROOT)}")
    return path.read_text()


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label} missing expected text: {needle}")


def assert_not_contains(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise AssertionError(f"{label} still contains forbidden text: {needle}")


def assert_core_prompt_gateway_optional(text: str, label: str) -> None:
    forbidden = [
        "Create Unity AI Gateway Endpoint",
        "Create an Unity AI Gateway endpoint",
        "provision the AI Gateway",
        "AI Gateway is required",
        "gateway live; DAB-deployed",
    ]
    for needle in forbidden:
        assert_not_contains(text, needle, label)


def find_sql_row(sql: str, tag: str) -> str:
    marker = f"'{tag}'"
    start = sql.find(marker)
    if start == -1:
        raise AssertionError(f"SQL row missing section_tag {tag}")
    next_insert = sql.find("INSERT INTO", start + len(marker))
    return sql[start: next_insert if next_insert != -1 else len(sql)]


def main() -> None:
    sql = read(SQL)

    for tag, order in EXPECTED_ORDER:
        row = find_sql_row(sql, tag)
        if not re.search(rf"\n{order},\n", row):
            raise AssertionError(f"{tag} SQL row does not use order_number {order}")

    agent_spec = read(SECTIONS / "38-agent_spec_design.md")
    assert_contains(agent_spec, "Save it to: docs/agent_spec.yaml", "agent_spec_design")
    assert_contains(agent_spec, "Do NOT create code", "agent_spec_design")
    assert_contains(agent_spec, "web search", "agent_spec_design")
    assert_contains(agent_spec, "mcp_research", "agent_spec_design")
    assert_contains(agent_spec, "agent_model", "agent_spec_design")
    assert_contains(agent_spec, "agent.model", "agent_spec_design")
    assert_contains(agent_spec, "databricks-claude-sonnet-4-6", "agent_spec_design")
    assert_contains(agent_spec, "docs/ui_design.md", "agent_spec_design")
    assert_contains(agent_spec, ".vibecoding-state.md", "agent_spec_design")
    assert_contains(agent_spec, "Prior App Context", "agent_spec_design")
    assert_contains(agent_spec, "step 03", "agent_spec_design")
    assert_contains(agent_spec, "step 04", "agent_spec_design")
    assert_contains(agent_spec, "steps 04-07", "agent_spec_design")
    assert_contains(agent_spec, "Bronze, Gold, Genie", "agent_spec_design")
    # Dynamic-eval contract: 38 authors tool-AGNOSTIC eval/governance fields under unified paths.
    assert_contains(agent_spec, "agent.benchmark_seeds.coverage_buckets", "agent_spec_design")
    assert_contains(agent_spec, "agent.benchmark_seeds.seed_examples", "agent_spec_design")
    assert_contains(agent_spec, "governance.scorer_suite.guidelines", "agent_spec_design")
    assert_contains(agent_spec, "governance.scorer_suite.custom_scorer_rules", "agent_spec_design")
    assert_contains(agent_spec, "governance.scorer_suite.judge_questions", "agent_spec_design")
    assert_contains(agent_spec, "governance.verification.smoke_test_cases", "agent_spec_design")
    assert_contains(agent_spec, "DO NOT predict tool selections", "agent_spec_design")
    # 38 must NOT carry tool-shaped scorer hints — those live in the Tool Plan.
    assert_not_contains(agent_spec, "tool_shaped_scorers", "agent_spec_design")

    tool_selection = read(SECTIONS / "39-agent_tool_selection.md")
    assert_contains(tool_selection, "docs/agent_spec.yaml", "agent_tool_selection")
    assert_contains(tool_selection, "docs/agent_tool_plan.yaml", "agent_tool_selection")
    assert_contains(tool_selection, "agent_sql_catalog", "agent_tool_selection")
    assert_contains(tool_selection, "agent_sql_schema", "agent_tool_selection")
    assert_contains(tool_selection, "readonly", "agent_tool_selection")
    assert_contains(tool_selection, "SELECT, DESCRIBE, EXPLAIN", "agent_tool_selection")
    assert_contains(tool_selection, "runtime_config", "agent_tool_selection")
    assert_contains(tool_selection, "llm:", "agent_tool_selection")
    assert_contains(tool_selection, 'provider: "databricks"', "agent_tool_selection")
    assert_contains(tool_selection, "api_base_url: null", "agent_tool_selection")
    assert_contains(tool_selection, 'api_mode: "databricks_openai_compatible"', "agent_tool_selection")
    assert_contains(tool_selection, "llm_api_base_url", "agent_tool_selection")
    assert_contains(tool_selection, "llm_api_mode", "agent_tool_selection")
    assert_contains(tool_selection, "Placeholder Handling", "agent_tool_selection")
    assert_contains(tool_selection, "ASK ME", "agent_tool_selection")
    assert_contains(tool_selection, "COPY the SCALAR value", "agent_tool_selection")
    assert_contains(tool_selection, "databricks-claude-sonnet-4-6", "agent_tool_selection")
    assert_contains(tool_selection, "# copied from agent.model", "agent_tool_selection")
    # Dynamic-eval contract: 39 mechanically derives tool-shaped scorers + smoke tests from selected_tools[].
    assert_contains(tool_selection, "Tool-Shaped Derivation", "agent_tool_selection")
    assert_contains(tool_selection, "verification.tool_smoke_tests", "agent_tool_selection")
    assert_contains(tool_selection, "runtime_guardrails.tool_shaped_scorers", "agent_tool_selection")
    assert_contains(tool_selection, "ka_citation_present", "agent_tool_selection")
    assert_contains(tool_selection, "RetrievalGroundedness", "agent_tool_selection")
    assert_contains(tool_selection, "sql_readonly_compliance", "agent_tool_selection")
    assert_contains(tool_selection, "genie_sql_correctness", "agent_tool_selection")
    assert_not_contains(
        tool_selection,
        'endpoint: "docs/agent_spec.yaml.agent.model"',
        "agent_tool_selection",
    )
    assert_not_contains(
        tool_selection,
        'name: "docs/agent_spec.yaml.agent.model"',
        "agent_tool_selection",
    )

    uc_foundation = read(SECTIONS / "40-uc_resources_foundation.md")
    assert_contains(uc_foundation, "Optional bring-your-own tool inputs", "uc_resources_foundation")
    assert_contains(uc_foundation, "agent_sql_catalog", "uc_resources_foundation")
    assert_contains(uc_foundation, "agent_sql_schema", "uc_resources_foundation")
    assert_not_contains(
        uc_foundation,
        "`bronze_table_metadata` (input_id 5)",
        "uc_resources_foundation",
    )
    assert_not_contains(
        uc_foundation,
        "`bronze_layer_creation` (input_id 7)",
        "uc_resources_foundation",
    )
    assert_not_contains(
        uc_foundation,
        "`genie_space` (input_id 11)",
        "uc_resources_foundation",
    )

    ka = read(SECTIONS / "42-knowledge_assistant_create.md")
    assert_contains(ka, "docs/agent_tool_plan.yaml", "knowledge_assistant_create")
    assert_contains(ka, "Skipped - KA not selected", "knowledge_assistant_create")
    assert_contains(ka, "Conditional execution", "knowledge_assistant_create")
    assert_not_contains(ka, "Bronze + Genie Space prompts also completed", "knowledge_assistant_create")

    clone = read(SECTIONS / "43-track_a_agent_app_clone_framework.md")
    assert_not_contains(clone, '"knowledge_assistant_create", gate: "KA READY"', "track_a_agent_app_clone_framework")
    assert_contains(clone, '"agent_tool_selection", gate: "Agent tool plan ready"', "track_a_agent_app_clone_framework")
    assert_contains(clone, 'runtime_model_ref: "docs/agent_tool_plan.yaml.runtime_config.llm"', "track_a_agent_app_clone_framework")
    assert_contains(clone, 'model_config_keys: ["llm_endpoint", "llm_api_base_url", "llm_api_mode"]', "track_a_agent_app_clone_framework")
    assert_contains(clone, "ModelConfig", "track_a_agent_app_clone_framework")
    assert_contains(clone, "No model endpoint may be hardcoded in Python", "track_a_agent_app_clone_framework")

    tools = read(SECTIONS / "44-track_a_agent_ka_genie_tools.md")
    assert_contains(tools, "docs/agent_tool_plan.yaml", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "Wire Selected Tools", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "SQL MCP", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "serving_endpoints", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "CAN_QUERY", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "Selected Backend Sources", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "Bring your own", "track_a_agent_ka_genie_tools")
    assert_contains(
        tools,
        'docs/agent_tool_plan.yaml.selected_tools[? type == "genie"]',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'docs/agent_tool_plan.yaml.selected_tools[? type == "vector_search"]',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'docs/agent_tool_plan.yaml.selected_tools[? type == "uc_function"]',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'docs/agent_tool_plan.yaml.selected_mcp_servers[? type == "external"]',
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        '`genie_space_id: "{genie_space_id}"`',
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "walks 6 ordered phases against `state://AgentSpec` and `state://DataSpec`",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "reads the resolved `state://AgentSpec` and `state://DataSpec`",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "captured upstream when the Genie Space was created over the Bronze tables",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "`genie_space` (input_id 11)",
        "track_a_agent_ka_genie_tools",
    )

    # SQL-level: the Agents Accelerator section header must list the visible
    # upstream path and must NOT list Bronze / Genie / AIBI Dashboard rows as
    # consumed by this section.
    header_anchor = "Phase 3: AppKit Integration     (input_ids 207, 208)"
    next_anchor = "-- Step 38:"
    h_start = sql.find(header_anchor)
    h_end = sql.find(next_anchor, h_start) if h_start != -1 else -1
    if h_start == -1 or h_end == -1:
        raise AssertionError("Could not locate Agents Accelerator section header in seed SQL")
    section_header = sql[h_start:h_end]
    for forbidden in (
        "bronze_table_metadata   (input_id 5)",
        "bronze_layer_creation   (input_id 7)",
        "aibi_dashboard          (input_id 12)",
        "genie_space             (input_id 11)",
    ):
        assert_not_contains(section_header, forbidden, "agents_accelerator_sql_header")
    for required in (
        "prd_generation              (input_id 1)",
        "cursor_copilot_ui_design    (input_id 3)",
        "workspace_setup_deploy      (input_id 4)",
        "setup_lakebase              (input_id 16)",
        "wire_ui_lakebase            (input_id 108)",
        "deploy_databricks_app       (input_id 110)",
    ):
        assert_contains(section_header, required, "agents_accelerator_sql_header")
    assert_contains(
        section_header,
        "Bronze, Gold, Genie, and AIBI Dashboard rows are NOT prerequisites of this section.",
        "agents_accelerator_sql_header",
    )

    eval_deploy = read(SECTIONS / "46-track_a_agent_eval_deploy.md")
    assert_contains(eval_deploy, "configured model route", "track_a_agent_eval_deploy")
    assert_contains(eval_deploy, "runtime_config.llm", "track_a_agent_eval_deploy")
    assert_core_prompt_gateway_optional(eval_deploy, "track_a_agent_eval_deploy")
    # Dynamic-eval contract: 46 unions Spec smoke cases with Plan tool smoke tests.
    assert_contains(eval_deploy, "agent_tool_plan_ref", "track_a_agent_eval_deploy")
    assert_contains(eval_deploy, "verification.tool_smoke_tests", "track_a_agent_eval_deploy")

    datasets = read(SECTIONS / "50-mlflow_evaluation_datasets.md")
    assert_contains(datasets, "agent_tool_plan_ref", "mlflow_evaluation_datasets")
    assert_contains(datasets, "verification.tool_smoke_tests", "mlflow_evaluation_datasets")
    assert_contains(datasets, "agent.benchmark_seeds.coverage_buckets", "mlflow_evaluation_datasets")
    assert_contains(datasets, "agent.benchmark_seeds.seed_examples", "mlflow_evaluation_datasets")

    scorers = read(SECTIONS / "51-mlflow_scorers_and_judges.md")
    assert_contains(scorers, "agent_tool_plan_ref", "mlflow_scorers_and_judges")
    assert_contains(scorers, "runtime_guardrails.tool_shaped_scorers", "mlflow_scorers_and_judges")
    assert_contains(scorers, "governance.scorer_suite.guidelines", "mlflow_scorers_and_judges")
    assert_contains(scorers, "RetrievalGroundedness", "mlflow_scorers_and_judges")
    assert_contains(scorers, "ONLY if KA or Vector Search appears in `selected_tools[]`", "mlflow_scorers_and_judges")

    eval_runs = read(SECTIONS / "52-mlflow_evaluation_runs_and_iteration.md")
    assert_contains(eval_runs, "agent_tool_plan_ref", "mlflow_evaluation_runs_and_iteration")
    assert_contains(eval_runs, "selected_tools", "mlflow_evaluation_runs_and_iteration")
    assert_contains(eval_runs, "tools present in `docs/agent_tool_plan.yaml.selected_tools[]`", "mlflow_evaluation_runs_and_iteration")

    for filename, label in [
        ("38-agent_spec_design.md", "agent_spec_design"),
        ("39-agent_tool_selection.md", "agent_tool_selection"),
        ("43-track_a_agent_app_clone_framework.md", "track_a_agent_app_clone_framework"),
        ("44-track_a_agent_ka_genie_tools.md", "track_a_agent_ka_genie_tools"),
        ("47-appkit_agent_app_proxy_chat.md", "appkit_agent_app_proxy_chat"),
        ("48-appkit_chat_feedback_mlflow.md", "appkit_chat_feedback_mlflow"),
    ]:
        assert_core_prompt_gateway_optional(read(SECTIONS / filename), label)

    gateway = read(SECTIONS / "55-mlflow_gateway_and_deployment.md")
    assert_contains(gateway, "optional", "mlflow_gateway_and_deployment")
    assert_contains(gateway, "pre-provisioned", "mlflow_gateway_and_deployment")
    assert_contains(gateway, "Core Track A does not depend on this step", "mlflow_gateway_and_deployment")

    skill = read(ROOT / "genai-agents" / "foundation" / "00b-agent-spec-and-tool-plan" / "SKILL.md")
    assert_contains(skill, "agent_sql_catalog", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "mcp_research", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "registry.modelcontextprotocol.io", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "docs/agent_tool_plan.yaml", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "agent_model", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "agent.model", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "Runtime Model Route Rule", "00b-agent-spec-and-tool-plan")

    # Pass 3: vibecoding-state hydrate_from_files operation + provenance v3.0
    state_skill = read(ROOT / "genai-agents" / "vibecoding-state" / "SKILL.md")
    assert_contains(state_skill, "hydrate_from_files", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "Operation: `hydrate_from_files`", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "agent_spec_yaml", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "agent_tool_plan_yaml", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "ui_design_md", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "prd_path", "vibecoding-state SKILL.md")
    assert_contains(state_skill, 'resolver_version: "3.0"', "vibecoding-state SKILL.md")
    assert_contains(state_skill, "hydrated_from_files: true", "vibecoding-state SKILL.md")
    assert_contains(state_skill, "optional: true", "vibecoding-state SKILL.md")
    assert_contains(
        state_skill,
        "docs/agent_spec.yaml.agent.model",
        "vibecoding-state SKILL.md",
    )

    spec_schema = read(ROOT / "genai-agents" / "vibecoding-state" / "references" / "spec-schema.md")
    assert_contains(spec_schema, "hydrated_from_files", "spec-schema.md")
    assert_contains(spec_schema, '"3.0"', "spec-schema.md")
    assert_contains(spec_schema, "resources.optional", "spec-schema.md")
    assert_contains(spec_schema, "hydrate_from_files", "spec-schema.md")

    # Pass 3: Step 40 must invoke hydrate_from_files between enter and the
    # foundation skill, and the captured state must record the hydration flags.
    assert_contains(
        uc_foundation,
        "`genai-agents/vibecoding-state` op `hydrate_from_files`",
        "uc_resources_foundation",
    )
    assert_contains(
        uc_foundation,
        'agent_spec_yaml: "docs/agent_spec.yaml"',
        "uc_resources_foundation",
    )
    assert_contains(
        uc_foundation,
        'agent_tool_plan_yaml: "docs/agent_tool_plan.yaml"',
        "uc_resources_foundation",
    )
    assert_contains(
        uc_foundation,
        'ui_design_md: "docs/ui_design.md"',
        "uc_resources_foundation",
    )
    assert_contains(
        uc_foundation,
        'prd_path: "docs/design_prd.md"',
        "uc_resources_foundation",
    )
    assert_contains(uc_foundation, "hydrated_from_files: true", "uc_resources_foundation")
    assert_contains(uc_foundation, 'resolver_version: "3.0"', "uc_resources_foundation")
    assert_contains(uc_foundation, "Phase 0.5 (hydrate)", "uc_resources_foundation")
    assert_contains(uc_foundation, "State hydration:", "uc_resources_foundation")

    # Pass 3: Step 42 branch (C) — must read docs/design_prd.md + agent_spec
    # capabilities, and must NOT consult state://DataSpec.glossary.
    assert_contains(
        ka,
        "docs/agent_spec.yaml.agent.capabilities",
        "knowledge_assistant_create",
    )
    assert_not_contains(
        ka,
        "state://DataSpec.glossary",
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        "docs/design_prd.md",
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        "Do **not** consult `state://DataSpec.*`",
        "knowledge_assistant_create",
    )

    # Pass 3.5 follow-up: Step 42 Resources Created checklist must split
    # into "If KA selected" vs "If KA not selected" branches mirroring
    # step 44's pattern. The skipped branch must capture the explicit
    # `n/a` stub and confirm step 44 cleanly ignores the KA family.
    assert_contains(
        ka,
        "If `docs/agent_tool_plan.yaml.knowledge_assistant.selected == true`",
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        "If `docs/agent_tool_plan.yaml.knowledge_assistant.selected == false`",
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        '`doc_qa_backend: "n/a"`, `ka_endpoint_name: "n/a"`, `knowledge_assistant_id: "n/a"`',
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        "no `tools/ka.py` is generated",
        "knowledge_assistant_create",
    )
    assert_contains(
        ka,
        "no KA TOOL span appears in MLflow",
        "knowledge_assistant_create",
    )

    # Pass 3: Step 44 — CAN_QUERY must target the scalar value at
    # runtime_config.llm.endpoint, never the literal YAML-path string. The
    # Expected Output must be conditional per Tool Plan family.
    assert_contains(
        tools,
        "Read the SCALAR value at docs/agent_tool_plan.yaml.runtime_config.llm.endpoint",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "NEVER grant on the literal YAML path string",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "grant `CAN_QUERY` on `docs/agent_spec.yaml.agent.model`",
        "track_a_agent_ka_genie_tools",
    )
    # Conditional Expected Output bullets
    assert_contains(
        tools,
        "Conditional on Tool Plan selection:",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "If `docs/agent_tool_plan.yaml.knowledge_assistant.selected == true`",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'If any `selected_tools[].type == "genie"`',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'If any `selected_tools[].type == "vector_search"`',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'If any `selected_tools[].type == "uc_function"`',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        'If any `selected_mcp_servers[].type == "external"`',
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "Model route (always applicable):",
        "track_a_agent_ka_genie_tools",
    )
    # Old unconditional bullets must be gone.
    assert_not_contains(
        tools,
        "- [ ] KA tool wired against `{ka_endpoint_name}`\n",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "- [ ] Genie tool wired against `{genie_space_id}`\n",
        "track_a_agent_ka_genie_tools",
    )

    # Pass 3.5: Step 44 prerequisite must cite `tool_recommendations` (loose) +
    # `selected_tools` (binding); the legacy `agent.tools[]` line must be gone.
    assert_contains(
        tools,
        "`tool_recommendations` populated",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "Final binding selections live in `docs/agent_tool_plan.yaml.selected_tools[]`",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "vibecoding-state.hydrate_from_files",
        "track_a_agent_ka_genie_tools",
    )
    assert_not_contains(
        tools,
        "- `agent.tools[]` populated in `docs/agent_spec.yaml`.\n",
        "track_a_agent_ka_genie_tools",
    )

    # Pass 3.5 follow-up: no remaining prose references that treat
    # `docs/agent_spec.yaml.agent.tools[]` as the canonical tool source. The
    # canonical, binding tool list is `docs/agent_tool_plan.yaml.selected_tools[]`;
    # `agent.tools[]` is a state-projection field only.
    assert_not_contains(
        tools,
        "docs/agent_spec.yaml.agent.tools",
        "track_a_agent_ka_genie_tools",
    )
    # The UC Functions row must point at the Tool Plan, not at agent.tools[].target.
    assert_not_contains(
        tools,
        "`agent.tools[].target` paths",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        '`selected_tools[? type == "uc_function"].target` paths',
        "track_a_agent_ka_genie_tools",
    )
    # The smoke-test step in "Steps to Apply" must cite selected_tools[] as the
    # canonical source (no compound "spec.agent.tools[] resolved through plan"
    # phrasing).
    assert_contains(
        tools,
        "smoke test against every tool declared in `docs/agent_tool_plan.yaml.selected_tools[]`",
        "track_a_agent_ka_genie_tools",
    )
    # The "One @function_tool per declared tool" best-practice row must count
    # entries in selected_tools[], not agent.tools[].
    assert_contains(
        tools,
        "Every entry in `docs/agent_tool_plan.yaml.selected_tools[]`",
        "track_a_agent_ka_genie_tools",
    )
    assert_contains(
        tools,
        "count entries in `selected_tools[]`",
        "track_a_agent_ka_genie_tools",
    )

    # Pass 3.5: vibecoding-state SKILL.md must document the
    # `tool_recommendations` + `selected_tools` projection rule and link to
    # `references/hydrator-prompt.md`.
    assert_contains(
        state_skill,
        "tool_recommendations.managed_databricks[]",
        "vibecoding-state SKILL.md",
    )
    assert_contains(
        state_skill,
        "Overlay `docs/agent_tool_plan.yaml.selected_tools[]`",
        "vibecoding-state SKILL.md",
    )
    assert_contains(
        state_skill,
        "binding selection wins over loose recommendation",
        "vibecoding-state SKILL.md",
    )
    assert_contains(
        state_skill,
        "references/hydrator-prompt.md",
        "vibecoding-state SKILL.md",
    )

    # Pass 3.5: hydrator-prompt.md must exist and ground the LLM driver.
    hydrator_prompt = read(
        ROOT / "genai-agents" / "vibecoding-state" / "references" / "hydrator-prompt.md"
    )
    assert_contains(hydrator_prompt, "Hydrator Prompt", "hydrator-prompt.md")
    assert_contains(hydrator_prompt, "hydrate_from_files", "hydrator-prompt.md")
    assert_contains(hydrator_prompt, 'resolver_version: "3.0"', "hydrator-prompt.md")
    assert_contains(hydrator_prompt, "hydrated_from_files: true", "hydrator-prompt.md")
    assert_contains(hydrator_prompt, "Post-hydration Guards", "hydrator-prompt.md")
    assert_contains(
        hydrator_prompt,
        "docs/agent_spec.yaml.agent.model",
        "hydrator-prompt.md",
    )
    assert_contains(
        hydrator_prompt,
        "docs/agent_tool_plan.yaml.runtime_config.llm.endpoint",
        "hydrator-prompt.md",
    )
    assert_contains(
        hydrator_prompt,
        "Tool Projection",
        "hydrator-prompt.md",
    )
    assert_contains(
        hydrator_prompt,
        "mutually exclusive on",
        "hydrator-prompt.md",
    )

    # Pass 3.5: resolver-prompt.md must no longer claim resolver_version is
    # "always 2.0", and must forbid regressing 3.0 -> 2.0.
    resolver_prompt = read(
        ROOT / "genai-agents" / "vibecoding-state" / "references" / "resolver-prompt.md"
    )
    assert_not_contains(
        resolver_prompt,
        '`spec_provenance.resolver_version` — always `"2.0"`.',
        "resolver-prompt.md",
    )
    assert_contains(resolver_prompt, "do NOT overwrite", "resolver-prompt.md")
    assert_contains(resolver_prompt, "regress `\"3.0\"` to `\"2.0\"`", "resolver-prompt.md")
    assert_contains(resolver_prompt, "hydrator-prompt.md", "resolver-prompt.md")

    # Pass 3.5: state-template.md must show the hydrated provenance + optional
    # resources example.
    state_template = read(
        ROOT / "genai-agents" / "vibecoding-state" / "references" / "state-template.md"
    )
    assert_contains(state_template, "Hydrated example", "state-template.md")
    assert_contains(state_template, "hydrated_from_files: true", "state-template.md")
    assert_contains(state_template, 'resolver_version: "3.0"', "state-template.md")
    assert_contains(state_template, "optional: true", "state-template.md")
    assert_contains(state_template, "no Lakehouse track", "state-template.md")

    # Pass 3.5: hydrated test fixture exists with the right shape.
    hydrated_fixture = read(
        ROOT
        / "genai-agents"
        / "vibecoding-state"
        / "references"
        / "test-fixtures"
        / "agents-only-hydrated-state.md"
    )
    assert_contains(hydrated_fixture, 'resolver_version: "3.0"', "agents-only-hydrated-state.md")
    assert_contains(hydrated_fixture, "hydrated_from_files: true", "agents-only-hydrated-state.md")
    assert_contains(hydrated_fixture, "optional: true", "agents-only-hydrated-state.md")
    assert_contains(hydrated_fixture, "no Lakehouse track", "agents-only-hydrated-state.md")
    assert_contains(hydrated_fixture, "## Agent", "agents-only-hydrated-state.md")
    assert_contains(hydrated_fixture, "tools:", "agents-only-hydrated-state.md")
    assert_contains(
        hydrated_fixture,
        "databricks-claude-sonnet-4-6",
        "agents-only-hydrated-state.md",
    )

    # Pass 3.5: Tool Plan schema reference must use the scalar endpoint name,
    # never the literal YAML-path string Pass 2 forbade.
    tool_plan_schema = read(
        ROOT
        / "genai-agents"
        / "foundation"
        / "00b-agent-spec-and-tool-plan"
        / "references"
        / "tool-plan-schema.md"
    )
    assert_not_contains(
        tool_plan_schema,
        'endpoint: "docs/agent_spec.yaml.agent.model"',
        "tool-plan-schema.md",
    )
    assert_not_contains(
        tool_plan_schema,
        'name: "docs/agent_spec.yaml.agent.model"',
        "tool-plan-schema.md",
    )
    assert_contains(
        tool_plan_schema,
        'endpoint: "databricks-claude-sonnet-4-6"',
        "tool-plan-schema.md",
    )
    assert_contains(
        tool_plan_schema,
        'name: "databricks-claude-sonnet-4-6"',
        "tool-plan-schema.md",
    )
    assert_contains(
        tool_plan_schema,
        "MUST be a **scalar Databricks serving-endpoint name**",
        "tool-plan-schema.md",
    )
    assert_contains(
        tool_plan_schema,
        "39-agent_tool_selection.md",
        "tool-plan-schema.md",
    )

    for legacy in LEGACY_FILES:
        text = read(legacy)
        assert_contains(text, "section_tag:", legacy.name)

    print("PASS agent track flow structure")
    _run_section_lint()


def _run_section_lint() -> int:
    """Run lint_section_prompts as INFORMATIONAL (non-strict) — prints
    failures but always returns 0 so out-of-scope thin sections don't
    block CI. Closeout (Task C.1) flips this to --strict once Phase 5+6
    files all pass."""
    proc = subprocess.run(
        [sys.executable,
         str(ROOT / "apps_lakebase" / "prompts" / "lint_section_prompts.py")],
        check=False,
    )
    if proc.returncode != 0:
        print("[section-lint] informational failures above — non-blocking until "
              "Phases 5+6 land (see retrospectives/plans/"
              "2026-04-29-section-prompts-quality-lift.md Task C.1).")
    return 0


if __name__ == "__main__":
    main()

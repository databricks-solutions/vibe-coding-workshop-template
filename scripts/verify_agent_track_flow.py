#!/usr/bin/env python3
from __future__ import annotations

import re
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

    tool_selection = read(SECTIONS / "39-agent_tool_selection.md")
    assert_contains(tool_selection, "docs/agent_spec.yaml", "agent_tool_selection")
    assert_contains(tool_selection, "docs/agent_tool_plan.yaml", "agent_tool_selection")
    assert_contains(tool_selection, "agent_sql_catalog", "agent_tool_selection")
    assert_contains(tool_selection, "agent_sql_schema", "agent_tool_selection")
    assert_contains(tool_selection, "readonly", "agent_tool_selection")
    assert_contains(tool_selection, "SELECT, DESCRIBE, EXPLAIN", "agent_tool_selection")

    ka = read(SECTIONS / "42-knowledge_assistant_create.md")
    assert_contains(ka, "docs/agent_tool_plan.yaml", "knowledge_assistant_create")
    assert_contains(ka, "Skipped - KA not selected", "knowledge_assistant_create")

    clone = read(SECTIONS / "43-track_a_agent_app_clone_framework.md")
    assert_not_contains(clone, '"knowledge_assistant_create", gate: "KA READY"', "track_a_agent_app_clone_framework")
    assert_contains(clone, '"agent_tool_selection", gate: "Agent tool plan ready"', "track_a_agent_app_clone_framework")

    tools = read(SECTIONS / "44-track_a_agent_ka_genie_tools.md")
    assert_contains(tools, "docs/agent_tool_plan.yaml", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "Wire Selected Tools", "track_a_agent_ka_genie_tools")
    assert_contains(tools, "SQL MCP", "track_a_agent_ka_genie_tools")

    skill = read(ROOT / "genai-agents" / "foundation" / "00b-agent-spec-and-tool-plan" / "SKILL.md")
    assert_contains(skill, "agent_sql_catalog", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "mcp_research", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "registry.modelcontextprotocol.io", "00b-agent-spec-and-tool-plan")
    assert_contains(skill, "docs/agent_tool_plan.yaml", "00b-agent-spec-and-tool-plan")

    for legacy in LEGACY_FILES:
        text = read(legacy)
        assert_contains(text, "section_tag:", legacy.name)

    print("PASS agent track flow structure")


if __name__ == "__main__":
    main()

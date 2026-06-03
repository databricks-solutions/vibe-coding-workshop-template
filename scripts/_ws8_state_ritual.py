#!/usr/bin/env python3
"""WS8b one-off: make the vibecoding-state enter/exit pair LOAD-BEARING across
every track fork (lakehouse / apps / agents).

Two mechanical edits, both idempotent:
  1. Every fork that already carries a `**State-lock:**` line gets a verify-write
     ritual + hard Gate-completion rule appended to that line, with the correct
     canonical state path for its track.
  2. The two design/plan forks that used `resolve_root` (gold_layer_design,
     usecase_plan) are converted to `enter`/`exit` and given a State-lock line so
     their state actually persists. gold_layer_design (the FIRST data-product
     step) bootstrap-creates the canonical DP state file.

Track -> canonical live state file:
  lakehouse -> <dp_bundle_root>/.vibecoding-state.md
  apps      -> <app_root>/.vibecoding-state.md
  agents    -> <agent_app_root>/.vibecoding-state.md
"""
import sys
from pathlib import Path

SECTIONS = Path(__file__).resolve().parent.parent / "apps_lakebase" / "prompts" / "sections"

LAKEHOUSE = "`<dp_bundle_root>/.vibecoding-state.md`"
APPS = "`<app_root>/.vibecoding-state.md`"
AGENTS = "`<agent_app_root>/.vibecoding-state.md`"

# Map fork stem (between `99-` and `.genie-code.md`) -> canonical state path token.
TRACK = {
    # lakehouse / data-product
    "bronze_layer_creation": LAKEHOUSE,
    "silver_layer_sdp": LAKEHOUSE,
    "gold_layer_pipeline": LAKEHOUSE,
    "genie_space": LAKEHOUSE,
    "aibi_dashboard": LAKEHOUSE,
    "deploy_lakehouse_assets": LAKEHOUSE,
    "deploy_di_assets": LAKEHOUSE,
    "gold_layer_design": LAKEHOUSE,
    "usecase_plan": LAKEHOUSE,
    # apps (AppKit)
    "cursor_copilot_ui_design": APPS,
    "deploy_databricks_app": APPS,
    "appkit_agent_app_proxy_chat": APPS,
    "appkit_chat_feedback_mlflow": APPS,
    # agents (Track A agent app + KA + mlflow agent ops)
    "agent_framework": AGENTS,
    "knowledge_assistant_create": AGENTS,
    "track_a_agent_app_clone_framework": AGENTS,
    "track_a_agent_ka_genie_tools": AGENTS,
    "track_a_agent_auth_memory": AGENTS,
    "track_a_agent_eval_deploy": AGENTS,
    "mlflow_gateway_and_deployment": AGENTS,
    "mlflow_production_monitoring_and_debugging": AGENTS,
}

RITUAL_SENTINEL = "mandatory ritual, not advisory"


def ritual(state_path: str) -> str:
    return (
        " **This `enter`/`exit` pair is a mandatory ritual, not advisory.** "
        f"Step 0's `enter` MUST locate — or, if this is the first prompt of the track, bootstrap-create — the canonical live state file at {state_path} "
        "(never the temporary `example/…` bootstrap path). The closing `exit` MUST append this prompt's Per-Step Log entry, Gate result, and `captured` vars to that file, then "
        "**re-read it and echo the appended section to prove the write landed**. "
        "**Gate completion rule:** this prompt is NOT complete until that re-read confirms the appended entry — the chat summary is NOT the state store."
    )


def stem_of(p: Path) -> str:
    return p.name[len("99-"):-len(".genie-code.md")]


def augment_statelock(text: str, state_path: str) -> tuple[str, int]:
    """Append the ritual to an existing single-line `**State-lock:**` paragraph."""
    out, n = [], 0
    for line in text.split("\n"):
        if line.startswith("**State-lock:**") and RITUAL_SENTINEL not in line:
            line = line.rstrip() + ritual(state_path)
            n += 1
        out.append(line)
    return "\n".join(out), n


def convert_resolve_root(text: str, stem: str, gate_label: str, captured: str, bootstrap: bool) -> tuple[str, int]:
    """For the design/plan forks: resolve_root -> enter, and insert a State-lock
    line just before the closing `**Gate:**` paragraph."""
    n = 0
    old_step0 = "Run `skills/vibecoding-state` operation `resolve_root`. Read these resolved values and use them literally throughout:"
    if old_step0 in text:
        if bootstrap:
            new_step0 = (
                f"Run `skills/vibecoding-state` operation `enter` (params: `prompt_id: \"{stem}\"`). "
                "This is the **FIRST data-product step**, so `enter` **bootstrap-creates** the canonical live state file at "
                "`<dp_bundle_root>/.vibecoding-state.md` from the template if absent (copying Workshop Choices from the prior `example/…` bootstrap file). "
                "Read these resolved values and use them literally throughout:"
            )
        else:
            new_step0 = (
                f"Run `skills/vibecoding-state` operation `enter` (params: `prompt_id: \"{stem}\"`) — it locates the canonical live state file at "
                "`<dp_bundle_root>/.vibecoding-state.md` (bootstrap-created by the first data-product step). "
                "Read these resolved values and use them literally throughout:"
            )
        text = text.replace(old_step0, new_step0, 1)
        n += 1

    if "**State-lock:**" not in text:
        statelock = (
            f"**State-lock:** this prompt runs between an `enter` (Step 0) and an `exit`. After the gate passes, run `skills/vibecoding-state` op `exit` — "
            f"params: `prompt_id: \"{stem}\"`, `gate: \"{gate_label}\"`, `captured: {{{captured}}}`."
            + ritual(LAKEHOUSE)
        )
        # Insert before the closing Gate paragraph.
        marker = "\n**Gate:**"
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx] + "\n" + statelock + "\n" + text[idx:]
            n += 1
    return text, n


def main() -> int:
    total = 0
    # 1) Augment every fork that has a State-lock line.
    for stem, state_path in TRACK.items():
        p = SECTIONS / f"99-{stem}.genie-code.md"
        if not p.exists():
            print(f"  MISSING: {p.name}")
            continue
        text = p.read_text(encoding="utf-8")
        # design/plan forks handled in step 2 (they have no State-lock yet)
        if stem in ("gold_layer_design", "usecase_plan"):
            continue
        new, n = augment_statelock(text, state_path)
        if n:
            p.write_text(new, encoding="utf-8")
            print(f"  {p.name}: +ritual on {n} State-lock line(s)")
            total += n

    # 2) Convert the two design/plan forks.
    gd = SECTIONS / "99-gold_layer_design.genie-code.md"
    text = gd.read_text(encoding="utf-8")
    new, n = convert_resolve_root(
        text, "gold_layer_design", "Gold design complete", "gold_design_path", bootstrap=True
    )
    if n:
        gd.write_text(new, encoding="utf-8")
        print(f"  {gd.name}: {n} edit(s) (resolve_root->enter + State-lock)")
        total += n

    up = SECTIONS / "99-usecase_plan.genie-code.md"
    text = up.read_text(encoding="utf-8")
    new, n = convert_resolve_root(
        text, "usecase_plan", "Use-case plan complete", "usecase_plan_path", bootstrap=False
    )
    if n:
        up.write_text(new, encoding="utf-8")
        print(f"  {up.name}: {n} edit(s) (resolve_root->enter + State-lock)")
        total += n

    print(f"WS8b state-ritual: {total} edit(s) across sections/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

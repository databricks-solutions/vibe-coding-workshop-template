#!/usr/bin/env python3
"""
Regression gate for the genie-code-integration effort.

ONE command that re-checks the "no regression" invariants from
retrospectives/plans/genie-code-integration/00-overview.md and reports PASS/FAIL:

  1. Environment-coupling audit (reuses scripts/audit_genie_compat.py `scan()`):
     - untouched areas must NOT increase vs the locked baseline (hard fail),
     - touched areas (--touched) are reported but allowed to change (they should drop),
     - total is reported with a delta (warn-only if it rose).
  2. Prompt chain round-trip: apps_lakebase/prompts/sync_markdown_to_seed.py --dry-run
     must report "No differences detected" (unless --allow-seed-diff, then report only).
     Auto-skips if the (git-ignored, separate-repo) prompts tree is absent.
  3. Optional `databricks bundle validate` when --bundle is passed and databricks.yml exists.

Baseline lives at genie_gate_baseline.json (repo root). Workflow:
  python scripts/genie_gate.py --update-baseline      # lock current state as the reference
  python scripts/genie_gate.py                         # check (no regression?) -> exit 0/1
  python scripts/genie_gate.py --touched apps_lakebase # while sweeping that area

The baseline should only be advanced (--update-baseline) AFTER a milestone's gate
passes and is reviewed, so each milestone ratchets coupling down and locks it in.
"""
import argparse
import json
import os
import subprocess
import sys
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_FILE = os.path.join(REPO_ROOT, "genie_gate_baseline.json")
ROOT_LABEL = "(root)"

sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))


def _area(file_path: str) -> str:
    parts = file_path.lstrip("." + os.sep).split(os.sep)
    return parts[0] if len(parts) > 1 else ROOT_LABEL


def current_counts() -> dict:
    """Run the audit from the repo root and bucket flags by area and class."""
    from audit_genie_compat import scan  # imported here so --help works without it

    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        rows = scan()
    finally:
        os.chdir(cwd)

    by_area_class = Counter()
    by_class = Counter()
    for r in rows:
        if r["class"] == "READ_ERROR":
            continue
        by_area_class[f"{_area(r['file'])}::{r['class']}"] += 1
        by_class[r["class"]] += 1
    return {
        "total": sum(by_class.values()),
        "by_class": dict(by_class),
        "by_area_class": dict(by_area_class),
    }


def load_baseline() -> dict | None:
    if not os.path.exists(BASELINE_FILE):
        return None
    with open(BASELINE_FILE, encoding="utf-8") as f:
        return json.load(f)


def write_baseline(counts: dict) -> None:
    payload = dict(counts)
    payload["_note"] = (
        "Locked regression baseline for genie-code-integration. "
        "Advance only after a milestone gate passes review."
    )
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"Baseline written: total={counts['total']} -> {BASELINE_FILE}")


def check_audit(touched: set[str]) -> bool:
    baseline = load_baseline()
    if baseline is None:
        print("NO BASELINE yet. Run: python scripts/genie_gate.py --update-baseline")
        return False
    cur = current_counts()
    base_ac = baseline.get("by_area_class", {})

    regressions = []
    keys = set(base_ac) | set(cur["by_area_class"])
    per_area_delta = Counter()
    for k in keys:
        area = k.split("::", 1)[0]
        delta = cur["by_area_class"].get(k, 0) - base_ac.get(k, 0)
        per_area_delta[area] += delta
        if delta > 0 and area not in touched:
            regressions.append((k, base_ac.get(k, 0), cur["by_area_class"].get(k, 0)))

    total_delta = cur["total"] - baseline["total"]
    print("=== audit gate ===")
    print(f"total: baseline {baseline['total']} -> current {cur['total']} "
          f"(delta {total_delta:+d})")
    if touched:
        print(f"touched (changes allowed): {', '.join(sorted(touched))}")
    moved = {a: d for a, d in sorted(per_area_delta.items()) if d != 0}
    if moved:
        print("per-area delta: " + ", ".join(f"{a} {d:+d}" for a, d in moved.items()))

    if regressions:
        print("\nFAIL — untouched areas increased (regression):")
        for k, b, c in sorted(regressions):
            print(f"  {k}: {b} -> {c}  (+{c - b})")
        return False
    if total_delta > 0:
        print("WARN — total rose, but only within touched areas. Confirm it's intended.")
    print("audit gate: PASS")
    return True


def check_roundtrip(allow_diff: bool) -> bool:
    prompts = os.path.join(REPO_ROOT, "apps_lakebase", "prompts")
    sync = os.path.join(prompts, "sync_markdown_to_seed.py")
    print("\n=== prompt round-trip gate ===")
    if not os.path.exists(sync):
        print("SKIP — prompts tree not present (separate-repo / git-ignored).")
        return True
    res = subprocess.run(
        [sys.executable, "sync_markdown_to_seed.py", "--dry-run"],
        cwd=prompts, capture_output=True, text=True,
    )
    tail = (res.stdout + res.stderr).strip().splitlines()[-1:] or [""]
    last = tail[0]
    clean = "No differences detected" in res.stdout
    print(f"sync --dry-run: {last}")
    if clean:
        print("round-trip gate: PASS (byte-clean)")
        return True
    if allow_diff:
        print("round-trip gate: PASS-WITH-DIFF (--allow-seed-diff; review the diff above)")
        return True
    print("round-trip gate: FAIL — seed not in sync. Re-extract/sync or pass --allow-seed-diff.")
    return False


def _tokens(text: str) -> set[str]:
    """Template variables `{like_this}` (excludes bundle `${vars}`)."""
    import re
    return set(re.findall(r"(?<![$\\])\{[A-Za-z0-9_]+\}", text or ""))


def _gate(text: str) -> str | None:
    """The backtick-quoted gate name from a `**Gate:** \`...\`` line, if any."""
    import re
    m = re.search(r"\*\*Gate:\*\*\s*`([^`]+)`", text or "")
    return m.group(1).strip() if m else None


def check_fork_parity() -> bool:
    """FORK_INTENT_PARITY (M07): every `*.genie-code.md` fork must preserve its default's
    intent surface — the template `{tokens}` (per-user-prefix invariant, decision #7) and the
    `**Gate:**` — and must NOT use bare `@.../SKILL.md` mentions (forks exist to give full
    clone-rooted paths). Mechanics may differ; intent may not. Auto-skips if the prompts tree
    is absent (git-ignored / separate repo)."""
    import re
    sections = os.path.join(REPO_ROOT, "apps_lakebase", "prompts", "sections")
    print("\n=== fork intent-parity gate ===")
    if not os.path.isdir(sections):
        print("SKIP — prompts tree not present (separate-repo / git-ignored).")
        return True
    sys.path.insert(0, os.path.join(REPO_ROOT, "apps_lakebase", "prompts"))
    try:
        from sync_markdown_to_seed import parse_markdown
    except Exception as e:  # pragma: no cover
        print(f"SKIP — cannot import parse_markdown ({e}).")
        return True

    from pathlib import Path
    files = sorted(Path(sections).glob("*.md"))
    forks, default_by_tag = [], {}
    for p in files:
        if p.name == "README.md":
            continue
        try:
            f = parse_markdown(p)
        except Exception as e:
            print(f"  WARN: cannot parse {p.name}: {e}")
            continue
        if p.name.endswith(".genie-code.md") or f.get("coding_assistant"):
            forks.append((p.name, f))
        else:
            default_by_tag[f.get("section_tag")] = f

    if not forks:
        print("no forks present — nothing to check. PASS")
        return True

    failures = []
    for name, fk in forks:
        tag = fk.get("section_tag")
        base = default_by_tag.get(tag)
        if base is None:
            failures.append(f"{name}: orphan fork — no default section with section_tag '{tag}'")
            continue
        base_text = (base.get("input_template", "") + "\n" + base.get("system_prompt", ""))
        fork_text = (fk.get("input_template", "") + "\n" + fk.get("system_prompt", ""))
        missing = _tokens(base_text) - _tokens(fork_text)
        if missing:
            failures.append(f"{name}: dropped template token(s) {sorted(missing)} (intent/prefix regression)")
        bg, fg = _gate(base_text), _gate(fork_text)
        if bg and bg != fg:
            failures.append(f"{name}: gate mismatch — default `{bg}` vs fork `{fg}`")
        bare = re.findall(r"@[\w./-]+/SKILL\.md", fork_text)
        if bare:
            failures.append(f"{name}: bare @-mention(s) {sorted(set(bare))} — use full skill_ref_root path")

    print(f"checked {len(forks)} fork(s) against {len(default_by_tag)} defaults")
    if failures:
        print("FAIL — fork intent-parity violations:")
        for f in failures:
            print(f"  {f}")
        return False
    print("fork intent-parity gate: PASS")
    return True


def check_deploy_fork_discipline() -> bool:
    """DEPLOY_FORK_DISCIPLINE (M07): any `*.genie-code.md` fork that drives a `bundle deploy`
    (a data-product / deploy fork) MUST carry the hardening signals that stop Genie Code
    from taking the frictionless-but-wrong path observed in the field:
      1. a no-direct-creation prohibition (DDL/CLONE is the bundle job's body, not a hand-run statement),
      2. a page-context recovery recipe (`databricks.yml not found` ⇒ navigate to the bundle page,
         don't fall back to direct SQL),
      3. a mechanism-aware gate (tables existing is "not sufficient" — the job must have deployed/run),
      4. a bundle-editor navigation directive (the field-confirmed fix for a blocked deploy is to open the
         bundle editor, not to abandon the bundle),
      5. a no-workaround / escape-hatch STOP rule (REST/SDK/direct-SQL fallback only on explicit operator
         authorization — the silent pivot to `jobs/create` was the observed regression).
    Static content check only; auto-skips if the prompts tree is absent."""
    import re
    sections = os.path.join(REPO_ROOT, "apps_lakebase", "prompts", "sections")
    print("\n=== deploy-fork discipline gate ===")
    if not os.path.isdir(sections):
        print("SKIP — prompts tree not present (separate-repo / git-ignored).")
        return True
    sys.path.insert(0, os.path.join(REPO_ROOT, "apps_lakebase", "prompts"))
    try:
        from sync_markdown_to_seed import parse_markdown
    except Exception as e:  # pragma: no cover
        print(f"SKIP — cannot import parse_markdown ({e}).")
        return True

    from pathlib import Path
    failures, checked = [], 0
    for p in sorted(Path(sections).glob("*.genie-code.md")):
        try:
            f = parse_markdown(p)
        except Exception as e:
            print(f"  WARN: cannot parse {p.name}: {e}")
            continue
        text = (f.get("input_template", "") or "") + "\n" + (f.get("system_prompt", "") or "")
        # Only deploy/data-product forks (those that drive a bundle deploy) are in scope.
        if "bundle deploy" not in text.lower():
            continue
        checked += 1
        low = text.lower()
        prohibition = (re.search(r"never\b[^\n]*\b(executecode|spark\.sql)", low) is not None
                       or "body of the bundle job" in low
                       or "do not fall back to direct sql" in low)
        page_recipe = "databricks.yml not found" in low
        mechanism_gate = "not sufficient" in low
        bundle_editor = "bundle editor" in low or "bundle-editor" in low
        escape_hatch = "escape hatch" in low
        if not prohibition:
            failures.append(f"{p.name}: missing no-direct-creation prohibition "
                            "(name DDL/CLONE as the bundle job's body; forbid executeCode/spark.sql).")
        if not page_recipe:
            failures.append(f"{p.name}: missing page-context recovery recipe "
                            "(`databricks.yml not found` ⇒ navigate to the bundle page, never direct SQL).")
        if not mechanism_gate:
            failures.append(f"{p.name}: gate is outcome-only — add a mechanism check "
                            "(tables existing is 'not sufficient'; require deploy + run).")
        if not bundle_editor:
            failures.append(f"{p.name}: missing bundle-editor navigation directive "
                            "(a blocked deploy is a wrong-page signal — open the bundle editor, don't abandon the bundle).")
        if not escape_hatch:
            failures.append(f"{p.name}: missing no-workaround / escape-hatch STOP rule "
                            "(REST/SDK/direct-SQL fallback only on explicit operator authorization).")

    print(f"checked {checked} deploy fork(s)")
    if failures:
        print("FAIL — deploy-fork discipline violations:")
        for f in failures:
            print(f"  {f}")
        return False
    print("deploy-fork discipline gate: PASS")
    return True


def check_lakehouse_fork_discipline() -> bool:
    """LAKEHOUSE_FORK_DISCIPLINE (WS5): the data-product / lakehouse `*.genie-code.md`
    forks must carry the field-hardening signals so Genie Code cannot take the
    frictionless-but-wrong path:
      (a) every lakehouse fork names its prerequisites via full `skill_ref_root`
          (`readSkillFile("skills/vibe-coding-workshop/...")`) AND has the
          preflight-acknowledgement hard gate;
      (b) every bundle-authoring lakehouse fork pins `source_linked_deployment: false`;
      (c) the Bronze fork carries the catalog no-create hard-stop language;
      (d) the Gold-pipeline fork forbids `saveAsTable` for gold loads and keeps the
          post-merge `validate_gold` task.
    Static content check only; auto-skips if the prompts tree is absent."""
    sections = os.path.join(REPO_ROOT, "apps_lakebase", "prompts", "sections")
    print("\n=== lakehouse-fork discipline gate ===")
    if not os.path.isdir(sections):
        print("SKIP — prompts tree not present (separate-repo / git-ignored).")
        return True
    sys.path.insert(0, os.path.join(REPO_ROOT, "apps_lakebase", "prompts"))
    try:
        from sync_markdown_to_seed import parse_markdown
    except Exception as e:  # pragma: no cover
        print(f"SKIP — cannot import parse_markdown ({e}).")
        return True
    from pathlib import Path

    # Bundle-authoring lakehouse forks (must pin source_linked_deployment: false).
    bundle_authoring = {
        "bronze_layer_creation", "silver_layer_sdp", "gold_layer_pipeline",
        "deploy_lakehouse_assets", "genie_space", "aibi_dashboard", "deploy_di_assets",
    }
    # Design/plan forks author no bundle (no source-linked requirement).
    design_plan = {"gold_layer_design", "usecase_plan"}
    lakehouse = bundle_authoring | design_plan

    failures, checked = [], 0
    for stem in sorted(lakehouse):
        p = Path(sections) / f"99-{stem}.genie-code.md"
        if not p.exists():
            failures.append(f"99-{stem}.genie-code.md: expected lakehouse fork is missing.")
            continue
        try:
            f = parse_markdown(p)
        except Exception as e:
            print(f"  WARN: cannot parse {p.name}: {e}")
            continue
        text = (f.get("input_template", "") or "") + "\n" + (f.get("system_prompt", "") or "")
        low = text.lower()
        checked += 1
        # (a) skill-load discoverability
        if 'readskillfile("skills/vibe-coding-workshop/' not in low:
            failures.append(f"{p.name}: prerequisites not named via full skill_ref_root "
                            "(`readSkillFile(\"skills/vibe-coding-workshop/...\")`).")
        if "preflight acknowledgement" not in low:
            failures.append(f"{p.name}: missing Step 1 preflight-acknowledgement hard gate.")
        # (b) source-linked off (bundle-authoring forks only)
        if stem in bundle_authoring and "source_linked_deployment" not in low:
            failures.append(f"{p.name}: bundle-authoring fork missing `source_linked_deployment: false`.")
        # (c) Bronze catalog no-create
        if stem == "bronze_layer_creation":
            if "no-create invariant" not in low and "hard stop" not in low:
                failures.append(f"{p.name}: missing catalog no-create hard-stop language.")
            if "create catalog" not in low:  # the prohibition must name CREATE CATALOG to forbid it
                failures.append(f"{p.name}: catalog rule does not name/forbid CREATE CATALOG.")
        # (d) Gold pipeline rules
        if stem == "gold_layer_pipeline":
            if "saveastable" not in low:
                failures.append(f"{p.name}: missing the saveAsTable-FORBIDDEN gold-load rule.")
            if "validate_gold" not in low:
                failures.append(f"{p.name}: missing the post-merge `validate_gold` task.")

    print(f"checked {checked} lakehouse fork(s)")
    if failures:
        print("FAIL — lakehouse-fork discipline violations:")
        for f in failures:
            print(f"  {f}")
        return False
    print("lakehouse-fork discipline gate: PASS")
    return True


def check_state_persistence_discipline() -> bool:
    """STATE_PERSISTENCE_DISCIPLINE (WS8): every track fork (lakehouse / apps / agents)
    that carries a `**State-lock:**` paragraph must make vibecoding-state persistence
    LOAD-BEARING, not advisory. Each in-scope fork must contain:
      - an `exit` invocation with `prompt_id:` and `gate:`,
      - the canonical track state path (`<dp_bundle_root|app_root|agent_app_root>/.vibecoding-state.md`),
      - the verify-write ritual sentinel ("mandatory ritual, not advisory"),
      - the hard completion rule ("NOT complete until ...").
    Spans lakehouse + apps + agents forks. Static content check; auto-skips if absent."""
    import re
    sections = os.path.join(REPO_ROOT, "apps_lakebase", "prompts", "sections")
    print("\n=== state-persistence discipline gate ===")
    if not os.path.isdir(sections):
        print("SKIP — prompts tree not present (separate-repo / git-ignored).")
        return True
    sys.path.insert(0, os.path.join(REPO_ROOT, "apps_lakebase", "prompts"))
    try:
        from sync_markdown_to_seed import parse_markdown
    except Exception as e:  # pragma: no cover
        print(f"SKIP — cannot import parse_markdown ({e}).")
        return True
    from pathlib import Path

    path_rx = re.compile(r"<(dp_bundle_root|app_root|agent_app_root)>/\.vibecoding-state\.md")
    failures, checked = [], 0
    for p in sorted(Path(sections).glob("*.genie-code.md")):
        try:
            f = parse_markdown(p)
        except Exception as e:
            print(f"  WARN: cannot parse {p.name}: {e}")
            continue
        text = (f.get("input_template", "") or "") + "\n" + (f.get("system_prompt", "") or "")
        if "State-lock:" not in text:
            continue  # not a state-bearing track fork
        checked += 1
        if "prompt_id:" not in text or "gate:" not in text:
            failures.append(f"{p.name}: State-lock missing an `exit` with `prompt_id:` + `gate:`.")
        if not path_rx.search(text):
            failures.append(f"{p.name}: missing the canonical track state path "
                            "(`<dp_bundle_root|app_root|agent_app_root>/.vibecoding-state.md`).")
        if "mandatory ritual, not advisory" not in text:
            failures.append(f"{p.name}: enter/exit not marked load-bearing "
                            "(missing the 'mandatory ritual, not advisory' verify-write ritual).")
        if "NOT complete until" not in text:
            failures.append(f"{p.name}: missing the hard Gate completion rule "
                            "('NOT complete until' the live state file write is confirmed by re-read).")

    print(f"checked {checked} state-bearing fork(s)")
    if failures:
        print("FAIL — state-persistence discipline violations:")
        for f in failures:
            print(f"  {f}")
        return False
    print("state-persistence discipline gate: PASS")
    return True


def check_bundle(profile: str | None) -> bool:
    print("\n=== bundle validate gate ===")
    if not os.path.exists(os.path.join(REPO_ROOT, "databricks.yml")):
        print("SKIP — no databricks.yml at repo root.")
        return True
    cmd = ["databricks", "bundle", "validate", "--target", "dev"]
    if profile:
        cmd += ["-p", profile]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    ok = res.returncode == 0
    print((res.stdout + res.stderr).strip()[-500:])
    print(f"bundle validate gate: {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update-baseline", action="store_true",
                    help="Write current counts as the locked baseline and exit.")
    ap.add_argument("--touched", nargs="*", default=[],
                    help="Areas being actively swept this milestone (increases there won't fail).")
    ap.add_argument("--allow-seed-diff", action="store_true",
                    help="Permit an intentional seed diff (e.g. during the M3 sweep).")
    ap.add_argument("--skip-roundtrip", action="store_true")
    ap.add_argument("--skip-fork-parity", action="store_true",
                    help="Skip the FORK_INTENT_PARITY check (M07 genie-code forks).")
    ap.add_argument("--skip-deploy-discipline", action="store_true",
                    help="Skip the DEPLOY_FORK_DISCIPLINE check (M07 genie-code deploy forks).")
    ap.add_argument("--skip-lakehouse-discipline", action="store_true",
                    help="Skip the LAKEHOUSE_FORK_DISCIPLINE check (WS5 genie-code lakehouse forks).")
    ap.add_argument("--skip-state-discipline", action="store_true",
                    help="Skip the STATE_PERSISTENCE_DISCIPLINE check (WS8 enter/exit load-bearing).")
    ap.add_argument("--bundle", action="store_true",
                    help="Also run `databricks bundle validate --target dev`.")
    ap.add_argument("--profile", default=None,
                    help="Databricks CLI profile for --bundle (e.g. fevm-prashanth).")
    args = ap.parse_args()

    if args.update_baseline:
        write_baseline(current_counts())
        return 0

    ok = check_audit(set(args.touched))
    if not args.skip_roundtrip:
        ok = check_roundtrip(args.allow_seed_diff) and ok
    if not args.skip_fork_parity:
        ok = check_fork_parity() and ok
    if not args.skip_deploy_discipline:
        ok = check_deploy_fork_discipline() and ok
    if not args.skip_lakehouse_discipline:
        ok = check_lakehouse_fork_discipline() and ok
    if not args.skip_state_discipline:
        ok = check_state_persistence_discipline() and ok
    if args.bundle:
        ok = check_bundle(args.profile) and ok

    print("\n" + ("=" * 48))
    print("GATE RESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

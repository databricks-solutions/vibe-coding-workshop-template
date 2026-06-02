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
    if args.bundle:
        ok = check_bundle(args.profile) and ok

    print("\n" + ("=" * 48))
    print("GATE RESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

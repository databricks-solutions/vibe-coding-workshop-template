#!/usr/bin/env python3
"""
Audit the workshop repo for patterns that assume a LOCAL-ONLY environment
or that won't render identically across IDE+CLI and Genie Code.

This is the Phase 0 baseline tool for the genie-code-integration metaplan
(see retrospectives/genie-code-refactor-handoff.md, Section 3.2). It is a
faithful port of the handoff's audit_genie_compat.py with two sanctioned
adaptations, called out by the handoff itself ("Adjust if your clone layout
differs"):

  1. ROOTS scans this single repo (".") because the companion
     vibe-coding-workshop-app repo is not checked out in this workspace.
  2. SKIP_SUBSTR excludes non-source/self-referential paths (.git, caches,
     the metaplan's own plans/ tree, and the handoff doc itself, which quotes
     these patterns as examples and would otherwise self-flag).

KEY POINT: we do NOT flag `databricks ...` CLI calls or shell usage as broken.
Genie Code HAS the CLI (via runDatabricksCli) and a shell. We flag only:
  - local-machine assumptions (laptop paths, local auth bootstrap, local Spark)
  - deploy instructions naming a script instead of the shared bundle verb
  - the Python bundle-config flavor (consistency risk)
  - Genie-Space-as-bundle-resource (needs version/deploy caveat)
  - in-session artifact creation (forbidden; define in bundle instead)
  - App deploy/scaffold (must route via runDatabricksCli)
  - bare-shell databricks invocations (route via runDatabricksCli)
  - client-specific navigation phrasing that should be templated

Output: genie_compat_audit.csv, classified for the Section 4 decision table.
Usage:
    python scripts/audit_genie_compat.py            # writes genie_compat_audit.csv
    python scripts/audit_genie_compat.py --out X.csv
"""
import os
import re
import csv
import argparse
from collections import Counter

# Adaptation 1: single repo. The companion app repo is not in this workspace.
ROOTS = ["."]
TEXT_EXT = (".md", ".sql", ".yml", ".yaml", ".txt", ".mdx", ".json")

# Adaptation 2: skip non-source / self-referential paths.
SKIP_SUBSTR = (
    os.sep + ".git" + os.sep,
    os.sep + "node_modules" + os.sep,
    os.sep + "__pycache__" + os.sep,
    os.sep + ".cursor" + os.sep,
    os.sep + "plans" + os.sep,
    "retrospectives" + os.sep,   # entire retrospectives/ tree is non-source (handoff, field guide, plans)
    "presentations" + os.sep,    # slide deck is non-source
    os.path.join("scripts", "audit_genie_compat.py"),
    # Generated baseline artifacts (avoid self-flagging on re-runs at gates).
    "skill_manifest.txt",
    "genie_compat_audit.csv",
)

PATTERNS = [
    (re.compile(r"databricks\s+auth\s+login|databricks\s+configure|DATABRICKS_TOKEN\s*="),
     "LOCAL_AUTH", "Local auth bootstrap; Genie Code is pre-authenticated.", "RULE_2_auth_to_ide_branch"),
    (re.compile(r"/Users/[\w\-/]+|/home/[\w\-/]+|~/[\w\-/]+|[A-Za-z]:\\\\|\.\./\.\."),
     "LOCAL_PATH", "Local absolute/relative path; resolve via project/UC.", "RULE_6_normalize_paths"),
    # Bare RELATIVE artifact paths in write/save instructions. On Genie Code the CWD is
    # page-type-dependent, so a bare `docs/design_prd.md` lands in the wrong place. Anchor every
    # artifact write to `<ARTIFACT_ROOT>/...` (the clone root captured by vibecoding-state.resolve_root).
    # Flags save/write/output-... <relpath> and create(s)/creating a `<relpath>` (backtick-guarded).
    # Does NOT flag anchored `<ARTIFACT_ROOT>/...`, absolute `/...`, `~/...`, `@`-mentions (read refs),
    # `${...}` / `{...}`-leading paths, or URLs.
    (re.compile(
        r"(?i)(?:"
        # save/output ... <relpath.ext>  (colon/to/as anchored; optional quote/backtick)
        r"(?:save(?:\s+(?:it|this|the\s+\w+|the\s+following[^:`\n]*))?\s*(?:to|as)"
        r"|saved\s+to|saves?\s+the\s+\w+\s+to|output(?:\s+file)?\s*(?::|\bto\b))"
        r"\s*:?\s*[`'\"]?"
        r"(?!<ARTIFACT_ROOT>|\$\{?ARTIFACT_ROOT|/|~|@|https?:|[A-Za-z]:\\|\{)"
        r"[\w.{}+-]*(?:/[\w.{}+-]+)*\.(?:md|csv|ya?ml|json|sql)\b"
        r"|"
        # write/create `<relpath.ext>`  (backtick-guarded — kills 'write Python/SQL', 'Write SKILL.md')
        r"(?:writes?|creat(?:e|es|ing)\s+(?:a|an|the))\s+`"
        r"(?!<ARTIFACT_ROOT>|/|~|@|\{)"
        r"[\w.{}+-]*(?:/[\w.{}+-]+)*\.(?:md|csv|ya?ml|json|sql)`"
        r")"),
     "BARE_ARTIFACT_PATH",
     "Bare relative artifact path in a write/save instruction; anchor to <ARTIFACT_ROOT> (clone root).",
     "RULE_6_normalize_paths"),
    (re.compile(r"databricks-connect|spark-submit\b|local\[\d*\]"),
     "LOCAL_SPARK", "Local Spark; use workspace serverless compute.", "RULE_4_workspace_compute"),
    (re.compile(r"\./scripts/\S*deploy\S*\.sh|bash\s+\S*deploy\S*\.sh"),
     "SCRIPT_DEPLOY", "Deploy via script; use `bundle deploy` (spine) via runDatabricksCli.", "RULE_1_shared_deploy"),
    (re.compile(r"\./scripts/\S+\.sh|setup-\S+\.sh|bootstrap\S*\.sh"),
     "SETUP_SCRIPT", "Setup script; move build logic into bundle resource.", "RULE_3_logic_to_bundle"),
    (re.compile(r"databricks_bundles|from\s+databricks\.bundles|@bundle\b|resources\.py"),
     "PY_BUNDLE_CONFIG", "Python bundle config; standardize on YAML resources.", "RULE_5_yaml_only"),
    (re.compile(r"genie_spaces?\s*:|genie[_\-]space.*resource|databricks_genie_space"),
     "GENIE_RESOURCE", "Genie Space: define as bundle resource; verify CLI version.", "RULE_8_genie_bundle_resource"),
    (re.compile(r"databricks\s+(jobs|pipelines|schemas|volumes)\s+create"
                r"|createAsset\s*\(|\.(jobs|pipelines|schemas|volumes|genie)\.create\s*\("
                r"|CREATE\s+(SCHEMA|VOLUME|TABLE)\b", re.I),
     "INSESSION_CREATE", "In-session creation; define as bundle resource instead (RULE_10).", "RULE_10_no_insession_create"),
    (re.compile(r"appkit|apps\s+init|apps\s+deploy|app\.yaml|npm\s+(install|run)|pnpm\b"),
     "APP_DEPLOY", "AppKit/App deploy; use apps init/deploy via runDatabricksCli.", "RULE_9_app_deploy"),
    (re.compile(r"(?<!run)(?<!`)\bdatabricks\s+(bundle|jobs|pipelines|apps|fs|workspace|secrets|catalogs)\b"),
     "SHELL_DATABRICKS", "Bare-shell databricks call; route via runDatabricksCli on Genie Code.", "RULE_1_shared_deploy"),
    (re.compile(r"open\s+(in|your)\s+(IDE|Cursor|VS\s?Code)|in\s+your\s+IDE", re.I),
     "CLIENT_NAV", "Client-specific navigation; template via client_context.", "RULE_0_template_preamble"),
]


def _skip(fp: str) -> bool:
    return any(s in fp for s in SKIP_SUBSTR)


def scan():
    rows = []
    for root in ROOTS:
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(TEXT_EXT):
                    continue
                fp = os.path.join(dirpath, fn)
                if _skip(fp):
                    continue
                try:
                    with open(fp, encoding="utf-8", errors="replace") as f:
                        for n, line in enumerate(f, 1):
                            for rx, cls, why, action in PATTERNS:
                                if rx.search(line):
                                    rows.append({"file": fp, "line": n, "class": cls,
                                                 "action": action, "why": why,
                                                 "text": line.strip()[:200]})
                except Exception as e:  # noqa: BLE001
                    rows.append({"file": fp, "line": 0, "class": "READ_ERROR",
                                 "action": "manual", "why": str(e), "text": ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="genie_compat_audit.csv")
    args = ap.parse_args()
    rows = scan()
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "line", "class", "action", "why", "text"])
        w.writeheader()
        w.writerows(rows)
    print("=== environment-coupling summary ===")
    for cls, n in Counter(r["class"] for r in rows).most_common():
        print(f"{cls:18s} {n:5d}")
    print(f"\nTotal flags: {len(rows)} -> {args.out}")


if __name__ == "__main__":
    main()

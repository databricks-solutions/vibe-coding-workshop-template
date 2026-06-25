#!/usr/bin/env python3
"""One-off: invert the Genie Code clone model in the Step 0 prose of every
`*.genie-code.md` fork.

Background (the probe that drives this): a folder's `databricks.yml` is recognized
as a Databricks Asset Bundle only when it sits inside a git working tree. So the
kickstart now `git clone`s the workshop repo INTO `artifact_root` (the user project,
git-backed -> bundles recognized) and merely *copies* the tree to the
`.assistant/skills/<repo>` discovery path. The old prose said the reverse ("the repo
itself is cloned at .assistant/skills ...; artifacts build separately in artifact_root").

All 31 forks carry ONE identical Step 0 `artifact_root` bullet, so this is a single
literal, idempotent string replacement. `skill_ref_root` is unchanged, so every fork's
`readSkillFile("skills/vibe-coding-workshop/...")` line and all gate path checks remain
valid — only the clone-vs-copy prose inverts.

Idempotent: re-running after the edit is a no-op (the OLD string is gone).
"""
from pathlib import Path
import glob

SECTIONS = Path(__file__).resolve().parent.parent / "apps_lakebase" / "prompts" / "sections"

OLD = (
    "- `artifact_root` = your workshop project root "
    "(e.g. `/Workspace/Users/<your-email>/vibe-coding-workshop`) — where all generated "
    "bundles/apps/docs build; the repo itself is cloned at "
    "`/Workspace/Users/<your-email>/.assistant/skills/vibe-coding-workshop` "
    "(skills load from there via `skill_ref_root`, NOT from `artifact_root`)"
)

NEW = (
    "- `artifact_root` = your workshop project root "
    "(e.g. `/Workspace/Users/<your-email>/vibe-coding-workshop`), a **git clone** of the "
    "workshop repo so generated bundles/apps/docs build in a git working tree and are "
    "recognized as Databricks Asset Bundles; the skill tree is **copied** to "
    "`/Workspace/Users/<your-email>/.assistant/skills/vibe-coding-workshop` for "
    "discovery (skills load from there via `skill_ref_root`, NOT from `artifact_root`)"
)


def main() -> int:
    total = 0
    for f in sorted(glob.glob(str(SECTIONS / "99-*.genie-code.md"))):
        p = Path(f)
        text = p.read_text(encoding="utf-8")
        if OLD in text:
            p.write_text(text.replace(OLD, NEW), encoding="utf-8")
            print(f"  {p.name}: Step 0 artifact_root line inverted")
            total += 1
        elif NEW in text:
            pass  # already inverted
        else:
            print(f"  {p.name}: SKIP — no matching Step 0 line (check for drift)")
    print(f"invert-clone Step 0: {total} fork(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

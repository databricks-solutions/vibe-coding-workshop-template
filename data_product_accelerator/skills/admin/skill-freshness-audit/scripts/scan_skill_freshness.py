#!/usr/bin/env python3
"""
Skill Freshness Scanner

Scans all SKILL.md files for last_verified dates and reports stale skills
based on volatility classification thresholds. Also checks upstream_sources
lineage metadata for sync staleness.

Discovery is repo-wide by default: every SKILL.md under the supplied root
(repo root by default) is included unless its path matches one of the
excluded path segments (`.git`, `node_modules`, `dist`, `build`, `.venv`,
`presentations`, `retrospectives`, `assets`, `references`).

Usage:
    python data_product_accelerator/skills/admin/skill-freshness-audit/scripts/scan_skill_freshness.py
    python ... --root /path/to/repo
    python ... --exclude '*tests*' --exclude '*sandbox*'

Output: Markdown-formatted report of stale skills grouped by volatility,
        plus upstream sync status.
"""

import argparse
import fnmatch
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

KNOWN_DOMAIN_ROOTS = {
    "data_product_accelerator",
    "genai-agents",
    "apps_lakebase",
}

DEFAULT_EXCLUDED_PATH_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    "presentations",
    "retrospectives",
    "assets",
    "references",
    ".cursor",
    ".pytest_cache",
}

# Staleness thresholds (days)
THRESHOLDS = {
    "high": 30,
    "medium": 90,
    "low": 180,
}

# Default volatility for skills without the field
DEFAULT_VOLATILITY = "medium"

# Upstream sync uses same thresholds as verification staleness
UPSTREAM_SYNC_THRESHOLDS = THRESHOLDS.copy()


def parse_frontmatter(skill_path: Path) -> dict:
    """Extract frontmatter metadata from a SKILL.md file."""
    content = skill_path.read_text(encoding="utf-8")

    # Match YAML frontmatter between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    frontmatter = match.group(1)
    metadata = {}

    # Extract name
    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    if name_match:
        metadata["name"] = name_match.group(1).strip().strip('"').strip("'")

    # Extract last_verified from metadata section
    lv_match = re.search(r"last_verified:\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?", frontmatter)
    if lv_match:
        metadata["last_verified"] = lv_match.group(1)

    # Extract volatility from metadata section
    vol_match = re.search(r"volatility:\s*(\w+)", frontmatter)
    if vol_match:
        metadata["volatility"] = vol_match.group(1).strip()

    # Extract version
    ver_match = re.search(r"version:\s*[\"']?([^\"'\n]+)[\"']?", frontmatter)
    if ver_match:
        metadata["version"] = ver_match.group(1).strip()

    # Extract upstream_sources metadata
    upstream_sources = parse_upstream_sources(frontmatter)
    metadata["upstream_sources"] = upstream_sources

    return metadata


def parse_upstream_sources(frontmatter: str) -> list[dict]:
    """Parse upstream_sources from YAML frontmatter.

    Handles two cases:
    - upstream_sources: []  (empty array — no upstream dependency)
    - upstream_sources: with nested items (has upstream dependencies)
    """
    # Check for explicit empty array
    empty_match = re.search(r"upstream_sources:\s*\[\s*\]", frontmatter)
    if empty_match:
        return []

    # Check if upstream_sources exists at all
    if "upstream_sources:" not in frontmatter:
        return None  # Field missing entirely

    sources = []

    # Find each upstream source entry (starts with "- name:")
    # We use a simple state-machine approach to parse the nested YAML
    in_upstream = False
    current_source = {}
    current_paths = []

    for line in frontmatter.split("\n"):
        stripped = line.strip()

        # Detect start of upstream_sources section
        if re.match(r"upstream_sources:", stripped):
            in_upstream = True
            continue

        if not in_upstream:
            continue

        # Detect end of upstream_sources section (next top-level key)
        if re.match(r"^  \w", line) and not line.startswith("    "):
            # We've left the upstream_sources block
            if current_source:
                if current_paths:
                    current_source["paths"] = current_paths
                sources.append(current_source)
            break

        # New source entry
        name_match = re.match(r"\s*-\s*name:\s*[\"']?([^\"'\n]+)[\"']?", line)
        if name_match:
            if current_source:
                if current_paths:
                    current_source["paths"] = current_paths
                sources.append(current_source)
            current_source = {"name": name_match.group(1).strip()}
            current_paths = []
            continue

        # Parse fields within a source entry
        repo_match = re.match(r"\s+repo:\s*[\"']?([^\"'\n]+)[\"']?", line)
        if repo_match:
            current_source["repo"] = repo_match.group(1).strip()
            continue

        rel_match = re.match(r"\s+relationship:\s*[\"']?([^\"'\n#]+)[\"']?", line)
        if rel_match:
            current_source["relationship"] = rel_match.group(1).strip()
            continue

        sync_match = re.match(r"\s+last_synced:\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?", line)
        if sync_match:
            current_source["last_synced"] = sync_match.group(1)
            continue

        commit_match = re.match(r"\s+sync_commit:\s*[\"']?([^\"'\n]+)[\"']?", line)
        if commit_match:
            current_source["sync_commit"] = commit_match.group(1).strip()
            continue

        # Path entries (within paths array)
        path_match = re.match(r'\s+-\s*["\']?([^"\'#\n]+)["\']?', line)
        if path_match and "paths" not in current_source:
            current_paths.append(path_match.group(1).strip())
            continue

    # Don't forget the last source
    if current_source:
        if current_paths:
            current_source["paths"] = current_paths
        sources.append(current_source)

    return sources if sources else []


def calculate_staleness(last_verified: str, volatility: str, today: datetime) -> dict:
    """Calculate staleness status for a skill."""
    try:
        verified_date = datetime.strptime(last_verified, "%Y-%m-%d")
    except ValueError:
        return {
            "days_since": -1,
            "threshold": THRESHOLDS.get(volatility, 90),
            "is_stale": True,
            "status": "INVALID DATE",
        }

    days_since = (today - verified_date).days
    threshold = THRESHOLDS.get(volatility, THRESHOLDS[DEFAULT_VOLATILITY])
    is_stale = days_since > threshold

    if days_since > threshold * 2:
        status = "CRITICAL"
    elif days_since > threshold:
        status = "STALE"
    elif days_since > threshold * 0.75:
        status = "WARNING"
    else:
        status = "OK"

    return {
        "days_since": days_since,
        "threshold": threshold,
        "is_stale": is_stale,
        "status": status,
    }


def discover_skill_paths(repo_root: Path, extra_excludes: list[str] | None = None) -> list[Path]:
    """Repo-wide discovery of SKILL.md files.

    Excludes vendored / build directories and reference / asset subtrees that
    are not themselves skills. Additional fnmatch-style globs can be supplied
    via `extra_excludes` (matched against the relative path).
    """
    extra_excludes = extra_excludes or []
    discovered: list[Path] = []
    for skill_md in repo_root.rglob("SKILL.md"):
        try:
            rel = skill_md.relative_to(repo_root)
        except ValueError:
            continue

        rel_str = str(rel)
        parts = rel.parts

        if any(part in DEFAULT_EXCLUDED_PATH_PARTS for part in parts):
            continue
        if any(fnmatch.fnmatch(rel_str, pat) for pat in extra_excludes):
            continue

        discovered.append(skill_md)
    return sorted(discovered)


def attribute_domain(skill_path: Path, repo_root: Path) -> str:
    """Compute a human-friendly domain string for a skill.

    Walks upward from the skill file until it hits a known top-level skill
    root (data_product_accelerator, genai-agents, apps_lakebase). The domain
    is the segment immediately under that root, joined with the top-level
    root for genai-agents subfolders so the output disambiguates between
    foundation / sdlc / tracks etc.

    Examples:
        apps_lakebase/skills/00-appkit-navigator/SKILL.md
            -> "apps_lakebase"
        genai-agents/foundation/01-mlflow-genai-foundation/SKILL.md
            -> "genai-agents/foundation"
        data_product_accelerator/skills/ml/00-ml-pipeline-setup/SKILL.md
            -> "ml"
        data_product_accelerator/skills/admin/self-improvement/SKILL.md
            -> "admin"
    """
    rel = skill_path.relative_to(repo_root)
    parts = rel.parts
    if not parts:
        return "root"

    top = parts[0]

    if top == "data_product_accelerator":
        if len(parts) >= 4 and parts[1] == "skills":
            return parts[2]
        return "data_product_accelerator"

    if top == "genai-agents":
        if len(parts) >= 3:
            return f"genai-agents/{parts[1]}"
        return "genai-agents"

    if top == "apps_lakebase":
        return "apps_lakebase"

    if top in KNOWN_DOMAIN_ROOTS:
        return top

    return parts[0] if len(parts) > 1 else "root"


def scan_skills(skill_paths: list[Path], repo_root: Path) -> list[dict]:
    """Scan supplied SKILL.md files and return freshness data."""
    results = []

    for skill_path in skill_paths:
        relative_path = skill_path.relative_to(repo_root)
        skill_dir = skill_path.parent.name
        domain = attribute_domain(skill_path, repo_root)

        metadata = parse_frontmatter(skill_path)

        results.append({
            "name": metadata.get("name", skill_dir),
            "path": str(relative_path),
            "domain": domain,
            "version": metadata.get("version", "unknown"),
            "last_verified": metadata.get("last_verified"),
            "volatility": metadata.get("volatility", None),
            "upstream_sources": metadata.get("upstream_sources"),
        })

    return results


def generate_report(results: list[dict], today: datetime) -> str:
    """Generate a markdown report of skill freshness and upstream sync status."""
    lines = [
        f"# Skill Freshness Report",
        f"",
        f"**Generated:** {today.strftime('%Y-%m-%d')}",
        f"**Skills Scanned:** {len(results)}",
        f"",
    ]

    # Separate skills into categories
    missing_metadata = [r for r in results if r["last_verified"] is None]
    has_metadata = [r for r in results if r["last_verified"] is not None]

    # Calculate staleness for skills with metadata
    for skill in has_metadata:
        vol = skill["volatility"] or DEFAULT_VOLATILITY
        staleness = calculate_staleness(skill["last_verified"], vol, today)
        skill.update(staleness)

    stale = [s for s in has_metadata if s["is_stale"]]
    ok = [s for s in has_metadata if not s["is_stale"]]

    # Upstream sync stats
    has_upstream = [r for r in results if r.get("upstream_sources") and len(r["upstream_sources"]) > 0]
    no_upstream = [r for r in results if r.get("upstream_sources") is not None and len(r.get("upstream_sources", [])) == 0]
    missing_upstream = [r for r in results if r.get("upstream_sources") is None]

    # Summary
    lines.extend([
        f"## Summary",
        f"",
        f"| Status | Count |",
        f"|---|---|",
        f"| OK | {len(ok)} |",
        f"| Stale | {len([s for s in stale if s['status'] == 'STALE'])} |",
        f"| Critical | {len([s for s in stale if s['status'] == 'CRITICAL'])} |",
        f"| Missing Metadata | {len(missing_metadata)} |",
        f"",
        f"### Upstream Lineage",
        f"",
        f"| Status | Count |",
        f"|---|---|",
        f"| Has Upstream Sources | {len(has_upstream)} |",
        f"| No Upstream (internal) | {len(no_upstream)} |",
        f"| Missing `upstream_sources` Field | {len(missing_upstream)} |",
        f"",
    ])

    # Critical & Stale skills (grouped by volatility)
    if stale:
        lines.extend([
            f"## Stale Skills (Action Required)",
            f"",
        ])

        for vol in ["high", "medium", "low"]:
            vol_stale = [s for s in stale if (s.get("volatility") or DEFAULT_VOLATILITY) == vol]
            if vol_stale:
                lines.extend([
                    f"### {vol.title()} Volatility (threshold: {THRESHOLDS[vol]} days)",
                    f"",
                    f"| Skill | Domain | Last Verified | Days Since | Status |",
                    f"|---|---|---|---|---|",
                ])
                for s in sorted(vol_stale, key=lambda x: -x["days_since"]):
                    lines.append(
                        f"| `{s['name']}` | {s['domain']} | {s['last_verified']} | {s['days_since']} | **{s['status']}** |"
                    )
                lines.append("")

    # Upstream Sync Status
    lines.extend([
        f"## Upstream Sync Status",
        f"",
    ])

    if has_upstream:
        # Calculate sync staleness for skills with upstream sources
        stale_syncs = []
        ok_syncs = []
        for skill in has_upstream:
            vol = skill.get("volatility") or DEFAULT_VOLATILITY
            for src in skill["upstream_sources"]:
                last_synced = src.get("last_synced")
                if last_synced:
                    sync_staleness = calculate_staleness(last_synced, vol, today)
                    entry = {
                        **skill,
                        "upstream_name": src.get("name", "unknown"),
                        "upstream_repo": src.get("repo", "unknown"),
                        "relationship": src.get("relationship", "unknown"),
                        "last_synced": last_synced,
                        "sync_commit": src.get("sync_commit", "unknown"),
                        "sync_days_since": sync_staleness["days_since"],
                        "sync_status": sync_staleness["status"],
                        "sync_is_stale": sync_staleness["is_stale"],
                    }
                    if sync_staleness["is_stale"]:
                        stale_syncs.append(entry)
                    else:
                        ok_syncs.append(entry)
                else:
                    stale_syncs.append({
                        **skill,
                        "upstream_name": src.get("name", "unknown"),
                        "upstream_repo": src.get("repo", "unknown"),
                        "relationship": src.get("relationship", "unknown"),
                        "last_synced": "never",
                        "sync_commit": "unknown",
                        "sync_days_since": -1,
                        "sync_status": "NEVER SYNCED",
                        "sync_is_stale": True,
                    })

        if stale_syncs:
            lines.extend([
                f"### Stale Upstream Syncs",
                f"",
                f"| Skill | Upstream | Relationship | Last Synced | Days Since | Status |",
                f"|---|---|---|---|---|---|",
            ])
            for s in sorted(stale_syncs, key=lambda x: -(x["sync_days_since"] if x["sync_days_since"] >= 0 else 9999)):
                lines.append(
                    f"| `{s['name']}` | {s['upstream_name']} | {s['relationship']} | {s['last_synced']} | {s['sync_days_since']} | **{s['sync_status']}** |"
                )
            lines.append("")

        if ok_syncs:
            lines.extend([
                f"### Synced Upstream Sources (OK)",
                f"",
                f"| Skill | Upstream | Relationship | Last Synced | Commit | Days Since |",
                f"|---|---|---|---|---|---|",
            ])
            for s in sorted(ok_syncs, key=lambda x: -x["sync_days_since"]):
                lines.append(
                    f"| `{s['name']}` | {s['upstream_name']} | {s['relationship']} | {s['last_synced']} | `{s['sync_commit']}` | {s['sync_days_since']} |"
                )
            lines.append("")

    if no_upstream:
        lines.extend([
            f"### No Upstream (Internal Methodology)",
            f"",
            f"These skills have `upstream_sources: []` — they are internal methodology with no upstream dependency.",
            f"",
            f"| Skill | Domain |",
            f"|---|---|",
        ])
        for s in sorted(no_upstream, key=lambda x: x["domain"]):
            lines.append(f"| `{s['name']}` | {s['domain']} |")
        lines.append("")

    # Missing upstream_sources field
    if missing_upstream:
        lines.extend([
            f"### Missing `upstream_sources` Field",
            f"",
            f"These skills don't have `upstream_sources` in their frontmatter yet.",
            f"",
            f"| Skill | Domain | Path |",
            f"|---|---|---|",
        ])
        for s in sorted(missing_upstream, key=lambda x: x["domain"]):
            lines.append(f"| `{s['name']}` | {s['domain']} | `{s['path']}` |")
        lines.append("")

    # Missing freshness metadata
    if missing_metadata:
        lines.extend([
            f"## Missing Freshness Metadata",
            f"",
            f"These skills don't have `last_verified` in their frontmatter yet.",
            f"",
            f"| Skill | Domain | Path |",
            f"|---|---|---|",
        ])
        for s in sorted(missing_metadata, key=lambda x: x["domain"]):
            lines.append(f"| `{s['name']}` | {s['domain']} | `{s['path']}` |")
        lines.append("")

    # OK skills
    if ok:
        lines.extend([
            f"## Verified Skills (OK)",
            f"",
            f"| Skill | Domain | Last Verified | Days Since | Volatility |",
            f"|---|---|---|---|---|",
        ])
        for s in sorted(ok, key=lambda x: -x["days_since"]):
            vol = s.get("volatility") or DEFAULT_VOLATILITY
            lines.append(
                f"| `{s['name']}` | {s['domain']} | {s['last_verified']} | {s['days_since']} | {vol} |"
            )
        lines.append("")

    return "\n".join(lines)


def find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until we find a directory that looks like the
    repo root (contains at least one of the known skill roots). Falls back to
    `start` if nothing matches within 10 levels.
    """
    candidate = start.resolve()
    for _ in range(10):
        if any((candidate / d).exists() for d in KNOWN_DOMAIN_ROOTS):
            return candidate
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return start.resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repo-wide skill freshness scanner. Scans every SKILL.md under the "
            "supplied root, classifies staleness by volatility, and reports "
            "upstream-source sync status."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Repository root to scan. Defaults to auto-detection by walking up "
            "from the current working directory until a directory containing "
            "data_product_accelerator/, genai-agents/, or apps_lakebase/ is found."
        ),
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help=(
            "Additional fnmatch-style glob patterns (matched against the "
            "skill path relative to the root) to exclude from the scan. "
            "Repeat the flag for multiple patterns."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    repo_root = args.root.resolve() if args.root else find_repo_root(Path.cwd())

    if not any((repo_root / d).exists() for d in KNOWN_DOMAIN_ROOTS):
        print(
            "ERROR: Could not locate a repository root containing one of "
            f"{sorted(KNOWN_DOMAIN_ROOTS)} starting from {repo_root}.",
            file=sys.stderr,
        )
        print(
            "Pass --root /path/to/repo or run from inside the repository.",
            file=sys.stderr,
        )
        sys.exit(1)

    skill_paths = discover_skill_paths(repo_root, extra_excludes=args.exclude)
    today = datetime.now()
    results = scan_skills(skill_paths, repo_root)
    report = generate_report(results, today)

    print(report)

    # Exit with code 1 if any skills are stale
    stale_count = sum(
        1 for r in results
        if r["last_verified"] is not None
        and calculate_staleness(
            r["last_verified"],
            r.get("volatility") or DEFAULT_VOLATILITY,
            today,
        )["is_stale"]
    )

    if stale_count > 0:
        print(f"\n⚠ {stale_count} skill(s) are stale and need verification.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

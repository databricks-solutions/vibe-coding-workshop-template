#!/usr/bin/env python3
"""
Skill Freshness Scanner

Scans all SKILL.md files for last_verified dates and reports stale skills
based on volatility classification thresholds. Also checks upstream_sources
lineage metadata for sync staleness.

Usage:
    python data_product_accelerator/skills/admin/skill-freshness-audit/scripts/scan_skill_freshness.py

Output: Markdown-formatted report of stale skills grouped by volatility,
        plus upstream sync status.
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

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


def scan_skills(root: Path) -> list[dict]:
    """Scan all SKILL.md files and return freshness data."""
    skills_dir = root / "skills"
    results = []

    for skill_path in sorted(skills_dir.rglob("SKILL.md")):
        relative_path = skill_path.relative_to(root)
        skill_dir = skill_path.parent.name
        domain = skill_path.parent.parent.name if skill_path.parent.parent != skills_dir else "root"

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


def main():
    # Find project root (look for skills directory)
    # Supports both workspace root (data_product_accelerator/skills/) and project root (skills/)
    cwd = Path.cwd()
    root = cwd

    # First check if data_product_accelerator/skills exists (workspace root)
    if (root / "data_product_accelerator" / "skills").exists():
        root = root / "data_product_accelerator"
    else:
        # Walk up to find skills directory
        for _ in range(10):
            if (root / "skills").exists():
                break
            root = root.parent
        else:
            print("ERROR: Could not find skills directory.", file=sys.stderr)
            print("Run this script from the workspace root or data_product_accelerator/ directory.", file=sys.stderr)
            sys.exit(1)

    today = datetime.now()
    results = scan_skills(root)
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

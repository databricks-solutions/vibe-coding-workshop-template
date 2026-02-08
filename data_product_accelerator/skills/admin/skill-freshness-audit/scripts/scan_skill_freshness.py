#!/usr/bin/env python3
"""
Skill Freshness Scanner

Scans all SKILL.md files for last_verified dates and reports stale skills
based on volatility classification thresholds.

Usage:
    python skills/admin/skill-freshness-audit/scripts/scan_skill_freshness.py

Output: Markdown-formatted report of stale skills grouped by volatility.
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

    return metadata


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
    skills_dir = root / ".cursor" / "skills"
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
        })

    return results


def generate_report(results: list[dict], today: datetime) -> str:
    """Generate a markdown report of skill freshness."""
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

    # Missing metadata
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
    cwd = Path.cwd()
    root = cwd

    # Walk up to find skills
    for _ in range(10):
        if (root / ".cursor" / "skills").exists():
            break
        root = root.parent
    else:
        print("ERROR: Could not find skills directory.", file=sys.stderr)
        print("Run this script from the project root or a subdirectory.", file=sys.stderr)
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

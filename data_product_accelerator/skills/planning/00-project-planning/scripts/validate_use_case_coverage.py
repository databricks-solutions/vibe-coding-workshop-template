#!/usr/bin/env python3
"""Validate use case catalog coverage: every question has artifacts, every artifact has questions.

Usage:
    python scripts/validate_use_case_coverage.py plans/use-case-catalog.md

Exit codes:
    0 — all checks pass
    1 — one or more validation failures
    2 — file not found or parse error
"""

import re
import sys
from pathlib import Path


def parse_use_case_catalog(text: str) -> list[dict]:
    """Extract use case cards from the catalog markdown."""
    uc_pattern = re.compile(
        r"###\s+(UC-\d+):\s*(.+?)(?=\n###\s+UC-|\n##\s+|$)",
        re.DOTALL,
    )
    use_cases = []

    for match in uc_pattern.finditer(text):
        uc_id = match.group(1)
        uc_name = match.group(2).split("\n")[0].strip()
        body = match.group(0)

        questions = _extract_questions(body)
        artifact_q_refs = _extract_artifact_question_refs(body)

        use_cases.append({
            "id": uc_id,
            "name": uc_name,
            "questions": questions,
            "artifact_q_refs": artifact_q_refs,
        })

    return use_cases


def _extract_questions(body: str) -> list[str]:
    """Pull numbered questions from a 'Business Questions This Use Case Answers' block."""
    q_block = re.search(
        r"\*\*Business Questions.*?:\*\*\s*\n((?:\s*\d+\..+\n?)+)",
        body,
    )
    if not q_block:
        return []
    return [
        line.strip()
        for line in q_block.group(1).strip().splitlines()
        if re.match(r"\s*\d+\.", line)
    ]


def _extract_artifact_question_refs(body: str) -> list[dict]:
    """Parse the 'Implementing Artifacts' table rows and their Q-refs."""
    rows = re.findall(
        r"\|\s*(\w[\w\s]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|",
        body,
    )
    artifacts = []
    for art_type, name, q_refs in rows:
        art_type = art_type.strip()
        if art_type.lower() in ("artifact type", "---", ""):
            continue
        q_list = re.findall(r"Q(\d+)", q_refs)
        artifacts.append({
            "type": art_type,
            "name": name.strip(),
            "questions_answered": [int(q) for q in q_list],
        })
    return artifacts


def validate(use_cases: list[dict]) -> tuple[list[str], list[str]]:
    """Run all validation checks. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    for uc in use_cases:
        qcount = len(uc["questions"])

        if qcount < 3:
            errors.append(f'{uc["id"]}: has {qcount} questions (minimum 3)')
        elif qcount > 5:
            warnings.append(f'{uc["id"]}: has {qcount} questions (recommended max 5)')

        q_numbers = set(range(1, qcount + 1))
        covered_qs: set[int] = set()
        for art in uc["artifact_q_refs"]:
            covered_qs.update(art["questions_answered"])
            if not art["questions_answered"]:
                warnings.append(
                    f'{uc["id"]}: artifact "{art["name"]}" has no question references'
                )

        orphan_qs = q_numbers - covered_qs
        if orphan_qs:
            q_labels = ", ".join(f"Q{q}" for q in sorted(orphan_qs))
            errors.append(f'{uc["id"]}: questions with no implementing artifact: {q_labels}')

    return errors, warnings


def print_report(
    use_cases: list[dict], errors: list[str], warnings: list[str]
) -> None:
    total_qs = sum(len(uc["questions"]) for uc in use_cases)
    total_artifacts = sum(len(uc["artifact_q_refs"]) for uc in use_cases)
    covered_count = 0
    for uc in use_cases:
        q_numbers = set(range(1, len(uc["questions"]) + 1))
        covered: set[int] = set()
        for art in uc["artifact_q_refs"]:
            covered.update(art["questions_answered"])
        covered_count += len(q_numbers & covered)

    pct = (covered_count / total_qs * 100) if total_qs else 0

    print("Use Case Coverage Report")
    print("=" * 40)
    print(f"Use cases:      {len(use_cases)}")
    print(f"Questions:      {total_qs}")
    print(f"Artifact maps:  {total_artifacts}")
    print(f"Coverage:       {pct:.0f}% ({covered_count}/{total_qs} questions have >= 1 artifact)")
    print()

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
    else:
        print("PASS: All questions have implementing artifacts.")

    if all(3 <= len(uc["questions"]) <= 5 for uc in use_cases):
        print("PASS: All use cases have 3-5 business questions.")

    if warnings:
        print()
        for w in warnings:
            print(f"WARN: {w}")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-use-case-catalog.md>", file=sys.stderr)
        return 2

    catalog_path = Path(sys.argv[1])
    if not catalog_path.exists():
        print(f"Error: file not found: {catalog_path}", file=sys.stderr)
        return 2

    text = catalog_path.read_text(encoding="utf-8")
    use_cases = parse_use_case_catalog(text)

    if not use_cases:
        print("Error: no use case cards found (expected '### UC-NNN: ...' headings)", file=sys.stderr)
        return 2

    errors, warnings = validate(use_cases)
    print_report(use_cases, errors, warnings)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

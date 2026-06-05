#!/usr/bin/env python3
"""WS7 one-off: username-prefix the data-product bundle folder/name across the
prompt sections (IDE defaults + genie-code forks). Idempotent — a negative
lookbehind prevents double-prefixing if re-run. Prints a per-file change count.

Renames (cross-client):
  {use_case_slug}_dab   -> {user_schema_prefix}_{use_case_slug}_dab
  <use_case_slug>_dab   -> {user_schema_prefix}_<use_case_slug>_dab
  booking_app_dab       -> {user_schema_prefix}_booking_app_dab   (example parity)
"""
import re
import sys
from pathlib import Path

SECTIONS = Path(__file__).resolve().parent.parent / "apps_lakebase" / "prompts" / "sections"

PREFIX = "{user_schema_prefix}_"
# Fixed-width negative lookbehind so a re-run never double-prefixes.
NOT_PREFIXED = r"(?<!\{user_schema_prefix\}_)"

PATTERNS = [
    (re.compile(NOT_PREFIXED + r"\{use_case_slug\}_dab"), PREFIX + "{use_case_slug}_dab"),
    (re.compile(NOT_PREFIXED + r"<use_case_slug>_dab"),  PREFIX + "<use_case_slug>_dab"),
    (re.compile(NOT_PREFIXED + r"booking_app_dab"),      PREFIX + "booking_app_dab"),
]


def main() -> int:
    total = 0
    for md in sorted(SECTIONS.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        orig = text
        n = 0
        for rx, repl in PATTERNS:
            text, c = rx.subn(repl, text)
            n += c
        if text != orig:
            md.write_text(text, encoding="utf-8")
            print(f"  {md.name}: {n} replacement(s)")
            total += n
    print(f"WS7 DAB-prefix: {total} replacement(s) across sections/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

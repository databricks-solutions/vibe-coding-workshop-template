"""Industry Data Model alignment overlay + crosswalk writer.

Phase 0 of the Gold Layer Design flow (worker: design-workers/08-industry-alignment).
Overlays the parsed/classified SOURCE schema with the entities from a normalized
industry reference manifest (context/industry_reference.yaml), producing an advisory
coverage crosswalk. It NEVER invents Gold tables — unmatched core/extended entities
are surfaced as gaps for human Waived/Planned disposition.

The crosswalk this writes (INDUSTRY_CROSSWALK.csv) is the single source of truth that
`design-workers/07-design-validation` Validation 6 loads, verifies, and scores.

Usage (standalone verification / CLI):
    python industry_overlay.py \
        --schema context/Wanderbricks_Schema.csv \
        --reference context/industry_reference.yaml \
        --out gold_layer_design/INDUSTRY_CROSSWALK.csv

Programmatic (inside the design flow):
    from industry_overlay import build_industry_overlay, write_crosswalk
    overlay = build_industry_overlay(classified, Path("context/industry_reference.yaml"))
    write_crosswalk(overlay, Path("gold_layer_design/INDUSTRY_CROSSWALK.csv"))
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import yaml

IMPORTANCE_WEIGHT = {"core": 3, "extended": 2, "optional": 1}


def _norm(name: str) -> str:
    """Normalize a name for matching.

    Lowercase, strip dim_/fact_/bridge_ prefixes, trailing _id, and a naive plural 's'
    so `customers` (source) and `customer` (reference entity/alias) match.
    """
    n = (name or "").lower().strip()
    n = re.sub(r"^(dim_|fact_|bridge_)", "", n)
    n = re.sub(r"_id$", "", n)
    n = re.sub(r"s$", "", n)
    return n


def build_industry_overlay(classified: dict, reference_path: Path) -> dict:
    """Overlay classified SOURCE tables with industry reference entities.

    Args:
        classified: {table_name: {"columns": [{"name": ...}, ...], ...}} — the output of
            the orchestrator's classify_tables() (only table + column names are used here).
        reference_path: path to the normalized industry_reference.yaml manifest.

    Returns:
        {applicable, crosswalk, unmatched_source, scorecard_seed, industry, source}.
        Advisory only — never mutates the design.
    """
    if not reference_path or not Path(reference_path).exists():
        return {
            "applicable": False,
            "note": "industry_reference.yaml absent — overlay skipped (industry alignment N/A).",
        }

    ref = yaml.safe_load(Path(reference_path).read_text()) or {}
    src_names = {_norm(t): t for t in classified}
    src_cols = {
        t: {_norm(c["name"]) for c in info.get("columns", [])}
        for t, info in classified.items()
    }

    crosswalk: list[dict] = []
    matched_src: set[str] = set()
    covered_w = applicable_w = 0

    for domain in ref.get("domains", []):
        for ent in domain.get("entities", []):
            ename = ent["name"]
            importance = ent.get("importance", "optional")
            weight = IMPORTANCE_WEIGHT.get(importance, 1)
            aliases = {_norm(a) for a in ([ename] + ent.get("aliases", []))}

            # 1) direct table match  2) absorbed (entity attributes present in a table)
            direct = next((src_names[a] for a in aliases if a in src_names), None)
            absorbed = [t for t, cols in src_cols.items() if aliases & cols]

            if direct:
                state, tables = "Covered", [direct]
            elif absorbed:
                state, tables = "Absorbed", absorbed
            else:
                state, tables = "Gap", []

            matched_src.update(tables)
            applicable_w += weight
            if state in {"Covered", "Absorbed"}:
                covered_w += weight

            crosswalk.append(
                {
                    "entity": ename,
                    "domain": domain.get("name", ""),
                    "importance": importance,
                    "sensitivity": ent.get("sensitivity", "none"),
                    "state": state,
                    "source_tables": tables,
                    "rationale": "" if state != "Gap" else "REVIEW: no source coverage",
                }
            )

    unmatched_source = sorted(set(classified) - matched_src)  # customer-specific extensions
    coverage = round(100 * covered_w / applicable_w) if applicable_w else 100

    _print_overlay(ref, crosswalk, unmatched_source, coverage)

    return {
        "applicable": True,
        "industry": ref.get("industry", "?"),
        "source": ref.get("source", "?"),
        "crosswalk": crosswalk,
        "unmatched_source": unmatched_source,
        "scorecard_seed": {"provisional_coverage_pct": coverage},
    }


def _print_overlay(ref: dict, crosswalk: list[dict], extensions: list[str], coverage: int) -> None:
    print(f"\n{'=' * 60}")
    print(f"Industry Coverage Overlay — {ref.get('industry', '?')} ({ref.get('source', '?')})")
    print(f"{'=' * 60}")
    print(f"Provisional core+ coverage: {coverage}%")
    order = sorted(crosswalk, key=lambda r: (r["state"] != "Gap", r["importance"]))
    for row in order:
        gap_flag = row["state"] == "Gap" and row["importance"] in {"core", "extended"}
        flag = "!! " if gap_flag else "   "
        tables = ", ".join(row["source_tables"]) or "-"
        print(f"{flag}{row['importance']:<8} {row['entity']:<24} {row['state']:<9} {tables}")
    if extensions:
        print(f"\nExtensions (source tables with no industry entity): {extensions}")


def write_crosswalk(overlay: dict, out_path: Path) -> None:
    """Persist the (dispositioned) crosswalk for Validation 6 to consume.

    Writes INDUSTRY_CROSSWALK.csv with columns:
        entity, domain, importance, sensitivity, state, gold_tables, rationale

    In Phase 0 the `state` reflects source coverage and `gold_tables` holds source tables;
    in Phase 2 the agent updates states (Waived/Planned) and rewrites `gold_tables` with the
    actual Gold dim/fact names before the final write.
    """
    if not overlay.get("applicable"):
        return
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["entity", "domain", "importance", "sensitivity", "state", "gold_tables", "rationale"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in overlay["crosswalk"]:
            gold = r.get("gold_tables", r.get("source_tables", []))
            writer.writerow(
                {
                    "entity": r["entity"],
                    "domain": r["domain"],
                    "importance": r["importance"],
                    "sensitivity": r.get("sensitivity", "none"),
                    "state": r["state"],
                    "gold_tables": "|".join(gold),
                    "rationale": r.get("rationale", ""),
                }
            )
    print(f"\nWrote crosswalk: {out_path} ({len(overlay['crosswalk'])} entities)")


def _load_classified_from_csv(csv_path: Path) -> dict:
    """Minimal source-schema loader for standalone CLI runs.

    Only table + column names are needed for the overlay match, so this is a lightweight
    parse of the customer schema CSV (columns: table_name, column_name, ...). Inside the
    real design flow, pass the richer output of the orchestrator's classify_tables() instead.
    """
    tables: dict = defaultdict(lambda: {"columns": []})
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            tables[row["table_name"]]["columns"].append({"name": row["column_name"]})
    return dict(tables)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Industry Data Model alignment overlay + crosswalk.")
    parser.add_argument("--schema", required=True, help="Source schema CSV (table_name, column_name, ...)")
    parser.add_argument("--reference", required=True, help="Normalized industry_reference.yaml manifest")
    parser.add_argument("--out", default="gold_layer_design/INDUSTRY_CROSSWALK.csv",
                        help="Output crosswalk CSV path")
    args = parser.parse_args()

    classified = _load_classified_from_csv(Path(args.schema))
    overlay = build_industry_overlay(classified, Path(args.reference))
    if overlay.get("applicable"):
        write_crosswalk(overlay, Path(args.out))
    else:
        print(overlay.get("note", "Overlay not applicable."))


if __name__ == "__main__":
    _main()

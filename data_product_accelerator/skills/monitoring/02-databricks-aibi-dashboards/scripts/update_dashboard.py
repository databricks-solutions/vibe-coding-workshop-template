#!/usr/bin/env python3
"""
Lakeview Dashboard JSON Utility

Robust, programmatic manipulation of Databricks AI/BI (Lakeview) dashboard
JSON files. Supports finding/updating datasets, widgets, query fields,
encodings, dataset custom calculations, hierarchy reordering, and field renaming.

Usage:
    python update_dashboard.py <input.lvdash.json> <output.lvdash.json> [--apply-canada-updates]

Functions are pure (return modified data); load/save are separate.
"""

import argparse
import copy
import json
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_dashboard(path: str) -> dict:
    """Load a Lakeview dashboard JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dashboard(path: str, data: dict, *, backup: bool = True) -> str:
    """Save dashboard JSON. Creates a timestamped backup of the original."""
    backup_path = None
    if backup and os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}.bak.{ts}"
        shutil.copy2(path, backup_path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return backup_path


# ---------------------------------------------------------------------------
# Finders
# ---------------------------------------------------------------------------

def find_dataset(data: dict, name: str) -> dict:
    """Return the dataset dict with the given name. Raises KeyError if missing."""
    for ds in data.get("datasets", []):
        if ds.get("name") == name:
            return ds
    available = [ds.get("name") for ds in data.get("datasets", [])]
    raise KeyError(f"Dataset '{name}' not found. Available: {available}")


def find_widget(data: dict, name: str) -> dict:
    """Return the widget dict with the given name. Searches all pages."""
    for page in data.get("pages", []):
        for item in page.get("layout", []):
            w = item.get("widget", {})
            if w.get("name") == name:
                return w
    all_names = []
    for page in data.get("pages", []):
        for item in page.get("layout", []):
            w = item.get("widget", {})
            if "name" in w:
                all_names.append(w["name"])
    raise KeyError(f"Widget '{name}' not found. Available: {all_names}")


def find_layout_item(data: dict, widget_name: str) -> dict:
    """Return the full layout item (position + widget) for a given widget name."""
    for page in data.get("pages", []):
        for item in page.get("layout", []):
            if item.get("widget", {}).get("name") == widget_name:
                return item
    raise KeyError(f"Layout item for widget '{widget_name}' not found.")


# ---------------------------------------------------------------------------
# Dataset Operations
# ---------------------------------------------------------------------------

def add_dataset_columns(data: dict, ds_name: str, columns: list[dict]) -> dict:
    """Add or merge custom calculated columns on a dataset.

    Each column is ``{"displayName": ..., "description": ..., "expression": ...}``.
    If a column with the same ``displayName`` already exists, it is updated.
    """
    data = copy.deepcopy(data)
    ds = find_dataset(data, ds_name)
    existing = ds.setdefault("columns", [])
    existing_map = {c["displayName"]: i for i, c in enumerate(existing)}

    for col in columns:
        if col["displayName"] in existing_map:
            existing[existing_map[col["displayName"]]] = col
        else:
            existing.append(col)
    return data


def update_dataset_query(data: dict, ds_name: str, new_query_lines: list[str]) -> dict:
    """Replace the ``queryLines`` of a dataset."""
    data = copy.deepcopy(data)
    ds = find_dataset(data, ds_name)
    ds["queryLines"] = new_query_lines
    return data


# ---------------------------------------------------------------------------
# Widget Query Operations
# ---------------------------------------------------------------------------

def get_widget_query(widget: dict) -> dict:
    """Return the first query object from a widget."""
    queries = widget.get("queries", [])
    if not queries:
        raise ValueError(f"Widget '{widget.get('name')}' has no queries.")
    return queries[0].get("query", {})


def update_widget_query_fields(data: dict, widget_name: str,
                                fields: list[dict]) -> dict:
    """Replace the ``fields`` array in a widget's query.

    Each field is ``{"name": ..., "expression": ...}``.
    """
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    q["fields"] = fields
    return data


def add_widget_query_fields(data: dict, widget_name: str,
                             new_fields: list[dict],
                             *, after: Optional[str] = None) -> dict:
    """Append fields to a widget query. If *after* is given, insert after that field."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    existing = q.setdefault("fields", [])

    if after:
        idx = next((i for i, f in enumerate(existing) if f["name"] == after), None)
        if idx is not None:
            for j, nf in enumerate(new_fields):
                existing.insert(idx + 1 + j, nf)
            return data

    existing_names = {f["name"] for f in existing}
    for nf in new_fields:
        if nf["name"] not in existing_names:
            existing.append(nf)
    return data


def rename_widget_query_field(data: dict, widget_name: str,
                               old_name: str, new_name: str) -> dict:
    """Rename a field in a widget's query (name + expression)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)

    for field in q.get("fields", []):
        if field["name"] == old_name:
            field["name"] = new_name
            if field.get("expression") == f"`{old_name}`":
                field["expression"] = f"`{new_name}`"
            break

    for order in q.get("orders", []):
        if order.get("expression") == f"`{old_name}`":
            order["expression"] = f"`{new_name}`"

    cgs = q.get("cubeGroupingSets", {})
    for s in cgs.get("sets", []):
        fn_list = s.get("fieldNames", [])
        for i, fn in enumerate(fn_list):
            if fn == old_name:
                fn_list[i] = new_name

    return data


# ---------------------------------------------------------------------------
# Widget Encoding Operations
# ---------------------------------------------------------------------------

def update_widget_encodings(data: dict, widget_name: str,
                             encodings: dict) -> dict:
    """Merge *encodings* into the widget's spec.encodings (deep merge at top level)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    enc = w.setdefault("spec", {}).setdefault("encodings", {})
    enc.update(encodings)
    return data


def set_widget_encoding_rows(data: dict, widget_name: str,
                              rows: list[dict]) -> dict:
    """Replace the ``rows`` encoding of a pivot widget."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    w["spec"]["encodings"]["rows"] = rows
    return data


def set_widget_encoding_values(data: dict, widget_name: str,
                                values: list[dict]) -> dict:
    """Replace the ``values`` encoding of a pivot widget (Pattern B)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    w["spec"]["encodings"]["values"] = values
    return data


def rename_encoding_field(data: dict, widget_name: str,
                           old_field: str, new_field: str) -> dict:
    """Rename a fieldName in all encoding arrays (rows, values, cell.fields)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    enc = w.get("spec", {}).get("encodings", {})

    for row in enc.get("rows", []):
        if row.get("fieldName") == old_field:
            row["fieldName"] = new_field

    for val in enc.get("values", []):
        if val.get("fieldName") == old_field:
            val["fieldName"] = new_field

    cell = enc.get("cell", {})
    for cf in cell.get("fields", []):
        if cf.get("fieldName") == old_field:
            cf["fieldName"] = new_field

    return data


# ---------------------------------------------------------------------------
# Reorder Helpers
# ---------------------------------------------------------------------------

def reorder_widget_query_fields(data: dict, widget_name: str,
                                 field_order: list[str]) -> dict:
    """Reorder a widget's query fields so that the named fields appear in *field_order*,
    followed by any remaining fields in their original order."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    fields = q.get("fields", [])

    by_name = {f["name"]: f for f in fields}
    ordered = []
    for name in field_order:
        if name in by_name:
            ordered.append(by_name.pop(name))
    for f in fields:
        if f["name"] in by_name:
            ordered.append(by_name.pop(f["name"]))
    q["fields"] = ordered
    return data


def reorder_widget_encoding_rows(data: dict, widget_name: str,
                                  row_order: list[str]) -> dict:
    """Reorder rows encodings to match *row_order* (list of fieldNames)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    rows = w["spec"]["encodings"].get("rows", [])

    by_field = {r["fieldName"]: r for r in rows}
    ordered = []
    for fn in row_order:
        if fn in by_field:
            ordered.append(by_field.pop(fn))
    for r in rows:
        if r["fieldName"] in by_field:
            ordered.append(by_field.pop(r["fieldName"]))
    w["spec"]["encodings"]["rows"] = ordered
    return data


def reorder_cube_grouping_sets(data: dict, widget_name: str,
                                field_order: list[str]) -> dict:
    """Reorder fieldNames inside cubeGroupingSets to match *field_order*."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    cgs = q.get("cubeGroupingSets", {})
    for s in cgs.get("sets", []):
        fn_list = s.get("fieldNames", [])
        if fn_list:
            fn_set = set(fn_list)
            new_list = [f for f in field_order if f in fn_set]
            remaining = [f for f in fn_list if f not in set(new_list)]
            s["fieldNames"] = new_list + remaining
    return data


def reorder_query_orders(data: dict, widget_name: str,
                          field_order: list[str]) -> dict:
    """Reorder the ``orders`` array to match *field_order* (by expression)."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    orders = q.get("orders", [])
    if not orders:
        return data

    by_expr = {}
    for o in orders:
        expr = o.get("expression", "")
        m = re.match(r"^`(.+)`$", expr)
        if m:
            by_expr[m.group(1)] = o

    new_orders = []
    for fn in field_order:
        if fn in by_expr:
            new_orders.append(by_expr.pop(fn))
    for o in orders:
        expr = o.get("expression", "")
        m = re.match(r"^`(.+)`$", expr)
        key = m.group(1) if m else expr
        if key in by_expr:
            new_orders.append(by_expr.pop(key))
    q["orders"] = new_orders
    return data


# ---------------------------------------------------------------------------
# Dataset Query Text Operations
# ---------------------------------------------------------------------------

def replace_in_dataset_query(data: dict, ds_name: str,
                              old: str, new: str) -> dict:
    """String-replace inside a dataset's queryLines."""
    data = copy.deepcopy(data)
    ds = find_dataset(data, ds_name)
    ds["queryLines"] = [line.replace(old, new) for line in ds.get("queryLines", [])]
    return data


def swap_dataset_query_lines(data: dict, ds_name: str,
                              line_a_contains: str,
                              line_b_contains: str) -> dict:
    """Swap ALL adjacent pairs of queryLines where line A contains *line_a_contains*
    and the immediately following line B contains *line_b_contains*.
    Handles UNION ALL queries with repeated column blocks."""
    data = copy.deepcopy(data)
    ds = find_dataset(data, ds_name)
    ql = ds.get("queryLines", [])
    i = 0
    while i < len(ql) - 1:
        if line_a_contains in ql[i] and line_b_contains in ql[i + 1]:
            ql[i], ql[i + 1] = ql[i + 1], ql[i]
            i += 2
        else:
            i += 1
    return data


def update_textbox(data: dict, widget_name: str, lines: list[str]) -> dict:
    """Replace the text content of a textbox widget."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    w["multilineTextboxSpec"] = {"lines": lines}
    if "textbox_spec" in w:
        del w["textbox_spec"]
    return data


def remove_widget_query_fields(data: dict, widget_name: str,
                                field_names: set[str]) -> dict:
    """Remove fields from a widget's query by name."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)
    q["fields"] = [f for f in q.get("fields", []) if f["name"] not in field_names]
    return data


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_dashboard(data: dict) -> list[str]:
    """Validate the dashboard structure. Returns a list of warning strings."""
    warnings = []

    for page in data.get("pages", []):
        page_name = page.get("displayName", page.get("name", ""))
        for item in page.get("layout", []):
            w = item.get("widget", {})
            wname = w.get("name", "unknown")
            queries = w.get("queries", [])
            if not queries:
                continue

            q = queries[0].get("query", {})
            field_names = {f["name"] for f in q.get("fields", [])}
            ds_name = q.get("datasetName", "")

            ds_columns = set()
            if ds_name:
                try:
                    ds = find_dataset(data, ds_name)
                    for col in ds.get("columns", []):
                        ds_columns.add(f'measure({col["displayName"]})')
                except KeyError:
                    warnings.append(
                        f"[{page_name}/{wname}] references missing dataset '{ds_name}'")

            all_known = field_names | ds_columns

            enc = w.get("spec", {}).get("encodings", {})
            for row in enc.get("rows", []):
                fn = row.get("fieldName", "")
                if fn and fn not in all_known:
                    warnings.append(
                        f"[{page_name}/{wname}] rows encoding '{fn}' not in query fields")

            for val in enc.get("values", []):
                fn = val.get("fieldName", "")
                if fn and fn not in all_known:
                    warnings.append(
                        f"[{page_name}/{wname}] values encoding '{fn}' not in query fields")

            cell = enc.get("cell", {})
            for cf in cell.get("fields", []):
                fn = cf.get("fieldName", "")
                if fn and fn not in all_known:
                    warnings.append(
                        f"[{page_name}/{wname}] cell encoding '{fn}' not in query fields or dataset columns")

    return warnings


# ---------------------------------------------------------------------------
# High-Level: Apply Canada Updates
# ---------------------------------------------------------------------------

# Pattern A dataset columns — same 9 calculations, using py_store_day_pairs denominator
CANADA_DATASET_COLUMNS = [
    {"displayName": "Store#",   "description": "Count of stores",
     "expression": "SUM(`stores`)"},
    {"displayName": "PY $",     "description": "APSD Prior Year Sales",
     "expression": "SUM(`py_sales`) / NULLIF(SUM(`py_store_day_pairs`), 0)"},
    {"displayName": "CY $",     "description": "APSD Current Year Sales",
     "expression": "SUM(`cy_sales`) / NULLIF(SUM(`cy_store_day_pairs`), 0)"},
    {"displayName": "% Chg",    "description": "APSD Sales YoY % Change",
     "expression": "(SUM(`cy_sales`) / NULLIF(SUM(`cy_store_day_pairs`), 0) - SUM(`py_sales`) / NULLIF(SUM(`py_store_day_pairs`), 0)) / NULLIF(SUM(`py_sales`) / NULLIF(SUM(`py_store_day_pairs`), 0), 0)"},
    {"displayName": "PY Txn",   "description": "APSD Prior Year Transactions",
     "expression": "SUM(`py_txn`) / NULLIF(SUM(`py_store_day_pairs`), 0)"},
    {"displayName": "CY Txn",   "description": "APSD Current Year Transactions",
     "expression": "SUM(`cy_txn`) / NULLIF(SUM(`cy_store_day_pairs`), 0)"},
    {"displayName": "Diff",     "description": "APSD Transaction Difference (CY - PY)",
     "expression": "SUM(`cy_txn`) / NULLIF(SUM(`cy_store_day_pairs`), 0) - SUM(`py_txn`) / NULLIF(SUM(`py_store_day_pairs`), 0)"},
    {"displayName": "Avg Txn",  "description": "Average Transaction Value (CY Sales / CY Txn)",
     "expression": "SUM(`cy_sales`) / NULLIF(SUM(`cy_txn`), 0)"},
    {"displayName": "Diff Txn", "description": "Avg Txn Difference (CY - PY)",
     "expression": "SUM(`cy_sales`) / NULLIF(SUM(`cy_txn`), 0) - SUM(`py_sales`) / NULLIF(SUM(`py_txn`), 0)"},
]

# Pattern A widget query fields — MEASURE() references
CANADA_MEASURE_FIELDS = [
    {"name": "measure(Store#)",   "expression": "MEASURE(`Store#`)"},
    {"name": "measure(PY $)",     "expression": "MEASURE(`PY $`)"},
    {"name": "measure(CY $)",     "expression": "MEASURE(`CY $`)"},
    {"name": "measure(% Chg)",    "expression": "MEASURE(`% Chg`)"},
    {"name": "measure(PY Txn)",   "expression": "MEASURE(`PY Txn`)"},
    {"name": "measure(CY Txn)",   "expression": "MEASURE(`CY Txn`)"},
    {"name": "measure(Diff)",     "expression": "MEASURE(`Diff`)"},
    {"name": "measure(Avg Txn)",  "expression": "MEASURE(`Avg Txn`)"},
    {"name": "measure(Diff Txn)", "expression": "MEASURE(`Diff Txn`)"},
]

# Pattern A cell encoding — references the MEASURE field names
CANADA_CELL_ENCODING = {
    "type": "multi-cell",
    "fields": [
        {"fieldName": "measure(Store#)",   "cellType": "text"},
        {"fieldName": "measure(PY $)",     "cellType": "text"},
        {"fieldName": "measure(CY $)",     "cellType": "text"},
        {"fieldName": "measure(% Chg)",    "cellType": "text"},
        {"fieldName": "measure(PY Txn)",   "cellType": "text"},
        {"fieldName": "measure(CY Txn)",   "cellType": "text"},
        {"fieldName": "measure(Diff)",     "cellType": "text"},
        {"fieldName": "measure(Avg Txn)",  "cellType": "text"},
        {"fieldName": "measure(Diff Txn)", "cellType": "text"},
    ],
    "displayAs": "columns",
}

CORRECT_HIERARCHY = [
    "zone_combination", "region_combination", "market_combination",
    "area_leader_name", "location_number",
]

CORRECT_HIERARCHY_ROWS_US = [
    {"fieldName": "zone_combination",   "displayName": "Zone"},
    {"fieldName": "region_combination", "displayName": "Region"},
    {"fieldName": "market_combination"},
    {"fieldName": "area_leader_name",   "displayName": "Area Leader"},
    {"fieldName": "location_number"},
]

CORRECT_HIERARCHY_ROWS_CA = [
    {"fieldName": "zone_combination",   "displayName": "Zone"},
    {"fieldName": "region_combination", "displayName": "Region"},
    {"fieldName": "market_combination", "displayName": "Market"},
    {"fieldName": "area_leader_name",   "displayName": "Area Leader"},
    {"fieldName": "location_number",    "displayName": "Store"},
]


def apply_hierarchy_fixes(data: dict) -> dict:
    """Fix hierarchy order and rename store_id -> location_number everywhere."""

    # --- US Franchise: rename store_id -> location_number ---
    data = rename_widget_query_field(data, "w-mp-us-franchise-hierarchy",
                                     "store_id", "location_number")
    data = rename_encoding_field(data, "w-mp-us-franchise-hierarchy",
                                 "store_id", "location_number")
    data = set_widget_encoding_rows(data, "w-mp-us-franchise-hierarchy",
                                    CORRECT_HIERARCHY_ROWS_US)
    data = reorder_widget_query_fields(data, "w-mp-us-franchise-hierarchy",
                                        CORRECT_HIERARCHY)
    data = reorder_cube_grouping_sets(data, "w-mp-us-franchise-hierarchy",
                                       CORRECT_HIERARCHY)
    data = reorder_query_orders(data, "w-mp-us-franchise-hierarchy",
                                 CORRECT_HIERARCHY)

    # Update dataset SQL: store_id -> location_number
    data = replace_in_dataset_query(data, "ds_us_franchise_hierarchy",
                                     "AS store_id", "AS location_number")

    # Fix ds_us_franchise_hierarchy SQL column order: swap market/region in SELECT
    data = swap_dataset_query_lines(data, "ds_us_franchise_hierarchy",
                                     "market_combination,", "region_combination,")
    # Fix GROUP BY order (appears in both Day and MTD UNION ALL halves)
    data = replace_in_dataset_query(
        data, "ds_us_franchise_hierarchy",
        "zone_combination, market_combination, region_combination,",
        "zone_combination, region_combination, market_combination,")

    # --- Canada Hierarchy: fix order (swap market/region) + rename ---
    data = rename_widget_query_field(data, "w-ca-hierarchy",
                                     "store_id", "location_number")
    data = rename_encoding_field(data, "w-ca-hierarchy",
                                 "store_id", "location_number")
    data = set_widget_encoding_rows(data, "w-ca-hierarchy",
                                    CORRECT_HIERARCHY_ROWS_CA)
    data = reorder_widget_query_fields(data, "w-ca-hierarchy",
                                        CORRECT_HIERARCHY)

    # Update dataset SQL: store_id -> location_number
    data = replace_in_dataset_query(data, "ds_canada_hierarchy",
                                     "AS store_id", "AS location_number")

    # Fix ds_canada_hierarchy SQL column order: swap market/region in SELECT
    data = swap_dataset_query_lines(data, "ds_canada_hierarchy",
                                     "market_combination,", "region_combination,")
    # Fix GROUP BY order
    data = replace_in_dataset_query(
        data, "ds_canada_hierarchy",
        "zone_combination, market_combination, region_combination,",
        "zone_combination, region_combination, market_combination,")

    # --- Sankey: swap stage2 (market) and stage3 (region) ---
    data = replace_in_dataset_query(data, "ds_sankey_sales_flow",
                                     "market_combination AS stage2",
                                     "region_combination AS stage2")
    data = replace_in_dataset_query(data, "ds_sankey_sales_flow",
                                     "region_combination AS stage3",
                                     "market_combination AS stage3")
    data = replace_in_dataset_query(
        data, "ds_sankey_sales_flow",
        "GROUP BY zone_combination, market_combination, region_combination",
        "GROUP BY zone_combination, region_combination, market_combination")

    # --- Fix Canada View textbox description ---
    try:
        data = update_textbox(data, "w-ca-title", [
            "# Canada View\n",
            "\n",
            "Detailed drill-down: Zone \u2192 Region \u2192 Market \u2192 Area Leader \u2192 Store. "
            "All metrics computed independently at each hierarchy level for correct APSD ratios.\n"
        ])
    except KeyError:
        pass

    return data


def _convert_widget_to_pattern_a(data: dict, widget_name: str,
                                  row_fields: list[dict],
                                  row_encodings: list[dict]) -> dict:
    """Convert a widget from Pattern B (inline expressions) to Pattern A
    (dataset columns + MEASURE). Replaces ALL query fields and encodings."""
    data = copy.deepcopy(data)
    w = find_widget(data, widget_name)
    q = get_widget_query(w)

    # Replace query fields: row dimensions + MEASURE references
    q["fields"] = row_fields + CANADA_MEASURE_FIELDS
    q["disaggregated"] = False

    # Replace encodings: rows + cell (remove values if present)
    enc = w["spec"]["encodings"]
    enc["rows"] = row_encodings
    enc["cell"] = copy.deepcopy(CANADA_CELL_ENCODING)
    enc.pop("values", None)

    return data


def apply_canada_updates(data: dict) -> dict:
    """Convert Canada pivots from Pattern B (inline) to Pattern A (dataset columns + MEASURE)."""

    # --- Add dataset columns to both Canada datasets ---
    data = add_dataset_columns(data, "ds_canada_corporate",
                                CANADA_DATASET_COLUMNS)
    data = add_dataset_columns(data, "ds_canada_hierarchy",
                                CANADA_DATASET_COLUMNS)

    # --- Canada Corporate: convert to Pattern A ---
    corp_row_fields = [
        {"name": "zone_combination", "expression": "`zone_combination`"},
        {"name": "currency",         "expression": "`currency`"},
    ]
    corp_row_encodings = [
        {"fieldName": "zone_combination", "displayName": "Zone"},
        {"fieldName": "currency",         "displayName": "$"},
    ]
    data = _convert_widget_to_pattern_a(
        data, "w-mp-canada-corporate", corp_row_fields, corp_row_encodings)

    # --- Canada Hierarchy: convert to Pattern A ---
    hier_row_fields = [
        {"name": "zone_combination",   "expression": "`zone_combination`"},
        {"name": "region_combination",  "expression": "`region_combination`"},
        {"name": "market_combination",  "expression": "`market_combination`"},
        {"name": "area_leader_name",    "expression": "`area_leader_name`"},
        {"name": "location_number",     "expression": "`location_number`"},
    ]
    data = _convert_widget_to_pattern_a(
        data, "w-ca-hierarchy", hier_row_fields, CORRECT_HIERARCHY_ROWS_CA)

    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Lakeview Dashboard JSON Utility")
    parser.add_argument("input", help="Input .lvdash.json file")
    parser.add_argument("output", help="Output .lvdash.json file")
    parser.add_argument("--apply-hierarchy-fixes", action="store_true",
                        help="Fix hierarchy order and rename store_id")
    parser.add_argument("--apply-canada-updates", action="store_true",
                        help="Add missing APSD fields to Canada pivots")
    parser.add_argument("--validate", action="store_true",
                        help="Validate and print warnings")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip creating a backup of the output file")
    args = parser.parse_args()

    data = load_dashboard(args.input)
    print(f"Loaded dashboard from {args.input}")
    print(f"  Datasets: {len(data.get('datasets', []))}")
    print(f"  Pages: {len(data.get('pages', []))}")

    if args.apply_hierarchy_fixes:
        data = apply_hierarchy_fixes(data)
        print("Applied hierarchy fixes (order + store_id -> location_number)")

    if args.apply_canada_updates:
        data = apply_canada_updates(data)
        print("Applied Canada visual updates (APSD fields + encodings)")

    if args.validate:
        warnings = validate_dashboard(data)
        if warnings:
            print(f"\nValidation: {len(warnings)} warning(s):")
            for w in warnings:
                print(f"  ⚠ {w}")
        else:
            print("\nValidation: OK — no issues found.")

    backup = save_dashboard(args.output, data, backup=not args.no_backup)
    print(f"\nSaved to {args.output}")
    if backup:
        print(f"Backup at {backup}")


if __name__ == "__main__":
    main()

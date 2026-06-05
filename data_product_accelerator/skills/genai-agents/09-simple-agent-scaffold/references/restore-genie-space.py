"""Restore a wiped Genie Space's serialized_space from a source-of-truth JSON.

Use when `GET /api/2.0/genie/spaces/{id}` returns empty `serialized_space` —
typically after an accidental `PATCH /api/2.0/data-rooms/{id}` with a partial
payload (see the anti-pattern block in SKILL.md).

Source config: the same JSON file your deploy_genie_spaces.py job consumes
(e.g. src/<project>_semantic/genie_configs/<space>.json). The file must contain
a top-level `serialized_space` dict that optionally references `${var_name}`
template variables (`${catalog}`, `${gold_schema}`, `${semantic_warehouse_id}`).

Usage:

    python restore-genie-space.py \
        --space-id 01f13ae0d34b1941bf0c1bd2128dcbd6 \
        --config-path src/.../genie_configs/travel_stays_intelligence.json \
        --catalog jane_doe_catalog \
        --gold-schema jane_d_booking_app_gold \
        --warehouse-id 3b1be27d7a807e80 \
        --profile DEFAULT

Recovery is idempotent — re-running against an already-healthy space is a no-op
from the caller's perspective (it simply re-asserts the same serialized_space).
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from databricks.sdk import WorkspaceClient


_VAR_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def substitute(obj, vars_: dict[str, str]):
    """Recursively substitute ${var_name} in any string values."""
    if isinstance(obj, str):
        return _VAR_PATTERN.sub(
            lambda m: vars_.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: substitute(v, vars_) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute(v, vars_) for v in obj]
    return obj


def sort_arrays(obj):
    """Sort tables/functions arrays by identifier — required by the Genie API."""
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in {"tables", "functions"} and isinstance(value, list):
                obj[key] = sorted(value, key=lambda x: x.get("identifier", ""))
            else:
                sort_arrays(value)
    elif isinstance(obj, list):
        for value in obj:
            sort_arrays(value)
    return obj


def restore(
    space_id: str,
    config_path: str,
    catalog: str,
    gold_schema: str,
    warehouse_id: str,
    profile: str | None = None,
) -> dict:
    with open(config_path) as fh:
        config = json.load(fh)

    if "serialized_space" not in config:
        raise ValueError(
            f"{config_path} has no top-level 'serialized_space' key. "
            f"Expected a Genie Space config produced by deploy_genie_spaces.py."
        )

    vars_ = {
        "catalog": catalog,
        "gold_schema": gold_schema,
        "semantic_warehouse_id": warehouse_id,
    }
    serialized = sort_arrays(substitute(config["serialized_space"], vars_))

    kwargs = {"profile": profile} if profile else {}
    w = WorkspaceClient(**kwargs)
    resp = w.api_client.do(
        "PATCH",
        f"/api/2.0/genie/spaces/{space_id}",
        body={"serialized_space": json.dumps(serialized)},
    )
    return resp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space-id", required=True, help="Genie Space ID to restore.")
    ap.add_argument("--config-path", required=True, help="Path to the source-of-truth JSON config.")
    ap.add_argument("--catalog", required=True, help="Value for ${catalog} in the config.")
    ap.add_argument("--gold-schema", required=True, help="Value for ${gold_schema} in the config.")
    ap.add_argument("--warehouse-id", required=True, help="Value for ${semantic_warehouse_id} in the config.")
    ap.add_argument("--profile", default=None, help="Databricks CLI profile (optional).")
    args = ap.parse_args()

    try:
        resp = restore(
            space_id=args.space_id,
            config_path=args.config_path,
            catalog=args.catalog,
            gold_schema=args.gold_schema,
            warehouse_id=args.warehouse_id,
            profile=args.profile,
        )
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    ok = "id" in resp or "space_id" in resp
    status = "OK" if ok else "FAIL"
    print(f"{status}: restored space {args.space_id}")
    print(json.dumps(resp, indent=2, default=str)[:500])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

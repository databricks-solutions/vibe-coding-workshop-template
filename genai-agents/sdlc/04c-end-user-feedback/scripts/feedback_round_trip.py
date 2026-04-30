"""Round-trip probe for the MLflow feedback assessment lifecycle.

Exercises log_feedback -> override_feedback -> delete_assessment -> re-log
against a known trace, then verifies the result via the SQL warehouse.

Usage:
    python feedback_round_trip.py \
        --trace-id "<bare or trace:/uri form>" \
        --assessments-table "<catalog>.<schema>.<prefix>_assessments" \
        --warehouse-id "$MLFLOW_TRACING_SQL_WAREHOUSE_ID" \
        --user-id "gate@example.com"

Env required for the warehouse step:
    DATABRICKS_HOST, DATABRICKS_TOKEN (or OAuth equivalent).

Exits 0 on success; non-zero with a printed reason on failure.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import mlflow
from mlflow.entities import AssessmentSource


def _to_assessments_id(trace_uri_or_id: str) -> str:
    """Skill 04c `to_assessments_id` — kept inline so this script is single-file."""
    return trace_uri_or_id  # modern Databricks runtimes accept the URI as-is.


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trace-id", required=True, help="Trace id (bare or trace:/...)")
    p.add_argument("--user-id", default="gate@example.com")
    p.add_argument("--assessments-table",
                   help="Fully-qualified UC table; required unless --api-only is set.")
    p.add_argument("--warehouse-id", default=os.environ.get("MLFLOW_TRACING_SQL_WAREHOUSE_ID"))
    p.add_argument("--warehouse-wait-seconds", type=int, default=10,
                   help="Seconds to sleep before warehouse verify (replication lag).")
    p.add_argument("--api-only", action="store_true",
                   help="Only exercise MLflow Assessment APIs; skip SQL warehouse read-back.")
    args = p.parse_args()

    trace_id = _to_assessments_id(args.trace_id)
    source = AssessmentSource(source_type="HUMAN", source_id=args.user_id)

    print(f"[1/4] log_feedback ...")
    first = mlflow.log_feedback(
        trace_id=trace_id, name="user_feedback", value=True,
        rationale="round-trip gate first write", source=source,
    )
    if not first or not first.assessment_id:
        print("FAIL: log_feedback returned no assessment_id"); return 2
    print(f"      assessment_id={first.assessment_id}")

    print(f"[2/4] override_feedback (in-place update) ...")
    overridden = mlflow.override_feedback(
        trace_id=trace_id, assessment_id=first.assessment_id,
        value=False, rationale="round-trip gate override",
    )
    if overridden.assessment_id != first.assessment_id:
        print("FAIL: override_feedback minted a fresh assessment_id"); return 3

    print(f"[3/4] delete_assessment ...")
    mlflow.delete_assessment(trace_id=trace_id, assessment_id=first.assessment_id)

    print(f"[4/4] re-log ...")
    second = mlflow.log_feedback(
        trace_id=trace_id, name="user_feedback", value=False,
        rationale="round-trip gate re-log", source=source,
    )
    if not second or not second.assessment_id:
        print("FAIL: re-log returned no assessment_id"); return 4
    if second.assessment_id == first.assessment_id:
        print("FAIL: re-log reused the deleted assessment_id"); return 5

    if args.api_only:
        print("PASS (assessment-API only; warehouse verify explicitly skipped)")
        return 0

    if not args.assessments_table or not args.warehouse_id:
        print("FAIL: --assessments-table and --warehouse-id are required unless --api-only is set")
        return 6

    print(f"      sleeping {args.warehouse_wait_seconds}s for warehouse replication ...")
    time.sleep(args.warehouse_wait_seconds)

    host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN")
    if not host or not token:
        print("FAIL: DATABRICKS_HOST and DATABRICKS_TOKEN are required for warehouse verify")
        return 7

    import json
    import urllib.request

    def sql_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    trace_forms = [trace_id]
    if trace_id.startswith("trace:/"):
        bare_id = trace_id.rsplit("/", 1)[-1]
        if bare_id not in trace_forms:
            trace_forms.append(bare_id)

    in_list = ", ".join(sql_quote(v) for v in trace_forms)
    statement = f"""
    SELECT assessment_id
    FROM {args.assessments_table}
    WHERE trace_id IN ({in_list}) AND name = 'user_feedback'
    ORDER BY create_time_ms DESC
    LIMIT 20
    """

    req = urllib.request.Request(
        f"https://{host}/api/2.0/sql/statements",
        data=json.dumps({
            "statement": statement,
            "warehouse_id": args.warehouse_id,
            "wait_timeout": "30s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        }).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode())

    rows = [r[0] for r in payload.get("result", {}).get("data_array", [])]

    if not rows:
        state = payload.get("status", {}).get("state", "<missing>")
        print(f"FAIL: warehouse returned no rows for the round-trip trace (state={state})"); return 8
    if rows[0] != second.assessment_id:
        print(f"FAIL: latest warehouse row ({rows[0]}) != re-log id ({second.assessment_id})"); return 9
    if first.assessment_id in rows[1:]:
        print("FAIL: deleted assessment leaked back into the warehouse view"); return 10

    print("PASS (full round-trip including warehouse verify)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

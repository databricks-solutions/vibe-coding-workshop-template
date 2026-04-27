# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
#   "pandas>=2.0",
# ]
# ///
"""Generic ``mlflow.genai.evaluate`` CLI: UC table → scorers → thresholds → JSON.

Stdout: JSON with ``run_id``, ``metrics``, ``pass``, ``threshold_checks``. Stderr: diagnostics.
Exits: 0 pass, 1 fail thresholds, 2 error."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

import mlflow
import pandas as pd
from mlflow.genai.scorers import RelevanceToQuery, Safety

E_OK, E_FAIL, E_ERR = 0, 1, 2


def _err(*a: Any, **k: Any) -> None:
    print(*a, file=sys.stderr, **k)


def _thresholds(raw: str) -> dict[str, float]:
    p = Path(raw)
    data = json.loads(p.read_text() if p.is_file() else raw)
    if not isinstance(data, dict):
        raise ValueError("thresholds: JSON object required")
    return {str(k): float(v) for k, v in data.items()}


def _out(v: Any) -> Any:
    if isinstance(v, dict):
        for k in ("content", "text", "output", "outputs", "message"):
            x = v.get(k)
            if isinstance(x, str):
                return x
        return json.dumps(v)
    return v


def _predict_from_file(path: str) -> Callable[..., Any]:
    spec = importlib.util.spec_from_file_location("_pred", Path(path).resolve())
    if not spec or not spec.loader:
        raise ImportError(path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    fn = getattr(m, "predict_fn", None)
    if not callable(fn):
        raise AttributeError(f"{path}: define predict_fn(inputs: dict) -> dict|str")

    def wrapped(**kwargs: Any) -> Any:
        return _out(fn(kwargs))

    return wrapped


def _extra_scorers(path: str) -> list[Any]:
    spec = importlib.util.spec_from_file_location("_scr", Path(path).resolve())
    if not spec or not spec.loader:
        raise ImportError(path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if hasattr(m, "get_scorers"):
        return list(m.get_scorers())
    if hasattr(m, "SCORERS"):
        return list(m.SCORERS)
    raise AttributeError(f"{path}: get_scorers() or SCORERS")


def _df(table: str) -> pd.DataFrame:
    try:
        from pyspark.sql import SparkSession

        sp = SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()
        return sp.table(table).toPandas()
    except Exception as e1:
        try:
            from mlflow.genai.datasets import get_dataset

            return get_dataset(name=table).to_df()
        except Exception as e2:
            raise RuntimeError(f"Spark: {e1!s}; get_dataset: {e2!s}") from e2


def _check(m: dict[str, float], t: dict[str, float]) -> tuple[bool, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    ok = True
    for name, need in t.items():
        got = m.get(name)
        if got is None:
            rows.append({"metric": name, "value": None, "required": need, "pass": False})
            ok = False
        else:
            passed = float(got) >= float(need)
            rows.append({"metric": name, "value": float(got), "required": float(need), "pass": passed})
            ok = ok and passed
    return ok, rows


def _parser() -> argparse.ArgumentParser:
    ep = """Threshold keys are evaluate() metric names (e.g. safety/mean). Examples:
  uv run run_evaluation.py --experiment-path /Shared/e --dataset-table c.s.t \\
    --thresholds '{"safety/mean":0.7,"relevance_to_query/mean":0.7}'
  uv run run_evaluation.py --experiment-path /Shared/e --dataset-table c.s.t \\
    --thresholds th.json --predict-module p.py --output out.json
"""
    p = argparse.ArgumentParser(description=__doc__, epilog=ep, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--experiment-path", required=True)
    p.add_argument("--dataset-table", required=True, help="UC table or managed dataset name")
    p.add_argument("--thresholds", required=True, help="JSON file path or inline JSON")
    p.add_argument("--predict-module", help="File with predict_fn(inputs: dict) -> dict|str")
    p.add_argument("--scorers-module", help="File with get_scorers() or SCORERS list")
    p.add_argument("--model-id", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output", help="Write JSON here (default stdout)")
    return p


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    try:
        th = _thresholds(a.thresholds)
    except Exception as e:
        _err("thresholds:", e)
        return E_ERR
    pred = _predict_from_file(a.predict_module) if a.predict_module else None
    scorers: list[Any] = [Safety(), RelevanceToQuery()]
    if a.scorers_module:
        try:
            scorers.extend(_extra_scorers(a.scorers_module))
        except Exception as e:
            _err("scorers-module:", e)
            return E_ERR
    try:
        df = _df(a.dataset_table)
    except Exception as e:
        _err("dataset:", e)
        return E_ERR
    if "inputs" not in df.columns:
        _err("missing column: inputs")
        return E_ERR
    if pred is None and "outputs" not in df.columns:
        _err("answer-sheet mode needs outputs column or --predict-module")
        return E_ERR
    if pred and "outputs" in df.columns:
        _err("note: outputs column ignored; using predict_fn")
    _err(f"rows={len(df)} table={a.dataset_table}")
    if a.dry_run:
        blob = json.dumps(
            {"dry_run": True, "rows": len(df), "columns": list(df.columns), "thresholds": th, "scorers": [type(s).__name__ for s in scorers]},
            indent=2,
        )
        (Path(a.output).write_text(blob) if a.output else print(blob))
        return E_OK
    mlflow.set_experiment(a.experiment_path)
    try:
        res = mlflow.genai.evaluate(data=df, scorers=scorers, predict_fn=pred, model_id=a.model_id)
    except Exception as e:
        _err("evaluate:", e)
        return E_ERR
    metrics = {k: float(v) for k, v in res.metrics.items()}
    passed, checks = _check(metrics, th)
    blob = json.dumps({"run_id": res.run_id, "metrics": metrics, "thresholds": th, "pass": passed, "threshold_checks": checks}, indent=2)
    (Path(a.output).write_text(blob) if a.output else print(blob))
    for c in checks:
        _err(("[OK]" if c["pass"] else "[FAIL]"), c["metric"], c.get("value"), ">=", c["required"])
    _err("overall:", "PASS" if passed else "FAIL")
    return E_OK if passed else E_FAIL


if __name__ == "__main__":
    sys.exit(main())

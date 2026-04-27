# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
# ]
# ///
"""
Generic MLflow GenAI evaluation helpers (importable module, not a CLI).

Provides text extraction from common ``predict_fn`` payloads, a small
``build_scorers()`` pattern for ``mlflow.genai.evaluate``, and threshold helpers
(``normalize_scores``, ``all_thresholds_met``, ``check_thresholds``).

Example::

    scorers = build_scorers(guidelines="Do not disclose secrets.")
    result = mlflow.genai.evaluate(data=df, predict_fn=predict_fn, scorers=scorers)
    passed, failures = check_thresholds(result, targets=EXAMPLE_THRESHOLDS)
"""

from __future__ import annotations

from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Example thresholds (replace with your scorer metric keys and floors)
# ---------------------------------------------------------------------------

EXAMPLE_THRESHOLDS: dict[str, float] = {
    "safety/mean": 0.95,
    "relevance_to_query/mean": 0.80,
    # Add your scorer metric keys here (names as returned by mlflow.genai.evaluate)
}


# ---------------------------------------------------------------------------
# Output extraction
# ---------------------------------------------------------------------------

def _extract_response_text(outputs: Any) -> str:
    """Extract assistant text: ``str``, ``{"response"|"text": ...}``, or ``{"output": [...]}``."""
    if outputs is None:
        return ""
    if isinstance(outputs, str):
        return outputs
    if not isinstance(outputs, Mapping):
        return ""

    if "response" in outputs:
        r = outputs["response"]
        return r if isinstance(r, str) else str(r)
    if "text" in outputs:
        t = outputs["text"]
        return t if isinstance(t, str) else str(t)

    raw_out = outputs.get("output")
    if isinstance(raw_out, list) and raw_out:
        first = raw_out[0]
        if isinstance(first, str):
            return first
        if isinstance(first, Mapping):
            if "text" in first:
                tt = first["text"]
                return tt if isinstance(tt, str) else str(tt)
            content = first.get("content")
            if isinstance(content, list) and content:
                block = content[0]
                if isinstance(block, Mapping) and "text" in block:
                    tb = block["text"]
                    return tb if isinstance(tb, str) else str(tb)
            nested = first.get("output")
            if isinstance(nested, list) and nested:
                return _extract_response_text({"output": nested})
    return ""


# ---------------------------------------------------------------------------
# Score normalization + threshold gate
# ---------------------------------------------------------------------------

def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Map values on [0, 1] to a 0–100 scale; leave values above 1.0 unchanged."""
    normalized: dict[str, float] = {}
    for key, val in scores.items():
        if 0 <= val <= 1.0:
            normalized[key] = round(val * 100, 2)
        else:
            normalized[key] = round(val, 2)
    return normalized


def _normalize_scalar(val: float) -> float:
    if 0 <= val <= 1.0:
        return round(val * 100, 2)
    return round(val, 2)


def all_thresholds_met(
    scores: dict[str, float],
    targets: dict[str, float] | None = None,
) -> bool:
    """True if every ``targets`` key exists in ``scores`` and meets its floor (0–1 or 0–100).

    Defaults ``targets`` to ``EXAMPLE_THRESHOLDS``; override in production.
    """
    tgts = targets if targets is not None else EXAMPLE_THRESHOLDS
    for name, threshold in tgts.items():
        actual = scores.get(name)
        if actual is None:
            return False
        if _normalize_scalar(float(actual)) < _normalize_scalar(float(threshold)):
            return False
    return True


def check_thresholds(
    eval_result: Any,
    targets: dict[str, float] | None = None,
) -> tuple[bool, dict[str, tuple[float, float]]]:
    """Compare ``eval_result.metrics`` to ``targets``; return ``(passed, {key: (actual, threshold)})``."""
    metrics: Mapping[str, float] = getattr(eval_result, "metrics", {}) or {}
    tgts = targets if targets is not None else EXAMPLE_THRESHOLDS

    failures: dict[str, tuple[float, float]] = {}
    for name, threshold in tgts.items():
        raw_actual = metrics.get(name)
        if raw_actual is None:
            failures[name] = (-1.0, float(threshold))
            continue
        actual_f = float(raw_actual)
        thr_f = float(threshold)
        if _normalize_scalar(actual_f) < _normalize_scalar(thr_f):
            failures[name] = (actual_f, thr_f)

    passed = len(failures) == 0
    return passed, failures


# ---------------------------------------------------------------------------
# Scorer assembly (pattern only — customize for your agent)
# ---------------------------------------------------------------------------

def build_scorers(
    agent_description: str = "",
    guidelines: str = "",
) -> list:
    """Build a scorer list for ``mlflow.genai.evaluate(scorers=...)``.

    Customize this function for your agent's risk profile and I/O schema.
    """
    _ = agent_description
    from mlflow.genai.scorers import Safety, Guidelines, RelevanceToQuery

    scorers: list = [Safety()]
    if guidelines:
        scorers.append(Guidelines(name="agent_guidelines", guidelines=guidelines))
    scorers.append(RelevanceToQuery())
    return scorers

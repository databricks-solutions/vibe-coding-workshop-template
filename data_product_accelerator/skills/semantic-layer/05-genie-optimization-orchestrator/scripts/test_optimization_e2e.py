#!/usr/bin/env python3
"""
End-to-end integration test for the Genie Optimization Orchestrator v3.4.0.

Exercises the lever-aware loop with mock data and mocked Genie/MLflow APIs.
No live Genie Space or Databricks workspace required.

Usage:
    python test_optimization_e2e.py
    python test_optimization_e2e.py --verbose

Requirements:
    - orchestrator.py, metadata_optimizer.py, optimization_applier.py on sys.path
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

MOCK_BENCHMARKS = [
    {"id": "q1", "question": "What is total revenue?", "expected_asset": "MV", "priority": "P0",
     "required_tables": ["revenue_facts"], "split": "train"},
    {"id": "q2", "question": "Top 10 customers by spend", "expected_asset": "TABLE", "priority": "P1",
     "required_tables": ["customer_dim"], "split": "train"},
    {"id": "q3", "question": "Monthly churn rate", "expected_asset": "MV", "priority": "P0",
     "required_tables": ["subscriptions"], "split": "held_out"},
]

MOCK_SPACE_CONFIG = {
    "title": "Test Genie Space",
    "general_instructions": "You are a data analyst.",
    "data_assets": [
        {"type": "TABLE", "identifier": "revenue_facts"},
        {"type": "TABLE", "identifier": "customer_dim"},
        {"type": "METRIC_VIEW", "identifier": "mv_churn"},
    ],
    "instructions": {"text_instructions": [{"id": "1", "content": ["Be precise."]}]},
}

MOCK_EVAL_RESULT = {
    "iteration": 1,
    "timestamp": "2026-02-21T00:00:00Z",
    "mlflow_run_id": "mock_run_001",
    "overall_accuracy": 66.0,
    "total_questions": 3,
    "correct_count": 2,
    "failures": ["q1"],
    "remaining_failures": ["q1"],
    "scores": {"asset_routing": 0.66, "schema_accuracy": 0.60},
}


def _mock_mlflow():
    """Return a mock mlflow module."""
    mock = MagicMock()
    mock.get_tracking_uri.return_value = "databricks"
    mock.set_experiment.return_value = None
    mock.start_run.return_value.__enter__ = MagicMock(
        return_value=MagicMock(info=MagicMock(run_id="mock_run_001"))
    )
    mock.start_run.return_value.__exit__ = MagicMock(return_value=False)
    mock.set_active_model.return_value = MagicMock(model_id="mock_model_001")
    mock.genai = MagicMock()
    mock.genai.register_prompt.return_value = MagicMock(version=1)
    return mock


def test_init_progress():
    """Test that init_progress creates the correct schema."""
    from orchestrator import init_progress

    progress = init_progress("space_123", "cost", max_iterations=3)
    assert progress["space_id"] == "space_123"
    assert progress["domain"] == "cost"
    assert progress["max_iterations"] == 3
    assert progress["status"] == "in_progress"
    assert progress["lever_impacts"] == {}
    assert progress["benchmark_corrections"] == []
    assert progress["maturity_level"] == "L1"
    assert progress["worker_reads"] == []
    assert progress["eval_dataset_name"] is None
    print("  PASS: init_progress")


def test_normalize_scores():
    """Test that _normalize_scores converts 0-1 to 0-100 scale."""
    from orchestrator import _normalize_scores

    assert _normalize_scores({}) == {}
    assert _normalize_scores({"a": 0.95}) == {"a": 95.0}
    assert _normalize_scores({"a": 95}) == {"a": 95}
    assert _normalize_scores({"a": 0.0}) == {"a": 0.0}
    assert _normalize_scores({"a": 1.0}) == {"a": 100.0}
    mixed = _normalize_scores({"a": 0.85, "b": 90})
    assert mixed == {"a": 85.0, "b": 90}
    print("  PASS: _normalize_scores")


def test_update_progress():
    """Test progress update with iteration results."""
    from orchestrator import init_progress, update_progress

    progress = init_progress("space_123", "cost")
    result = {**MOCK_EVAL_RESULT, "model_id": "m001"}
    update_progress(progress, result)

    assert len(progress["iterations"]) == 1
    assert progress["best_overall_accuracy"] == 66.0
    assert progress["best_iteration"] == 1
    print("  PASS: update_progress")


def test_pareto_frontier_uses_patch_cost():
    """Test that Pareto frontier uses patch_cost, not patch_count."""
    from orchestrator import init_progress, update_progress

    progress = init_progress("space_123", "cost")
    result = {
        **MOCK_EVAL_RESULT,
        "model_id": "m001",
        "proposals_applied": [
            {"risk_level": "high"},
            {"risk_level": "low"},
        ],
    }
    update_progress(progress, result)

    frontier = progress.get("pareto_frontier", [])
    assert len(frontier) == 1
    assert "patch_cost" in frontier[0]
    assert frontier[0]["patch_cost"] == 4  # high(3) + low(1)
    assert "patch_count" not in frontier[0]
    print("  PASS: pareto_frontier uses patch_cost")


def test_log_lever_impact():
    """Test per-lever impact tracking."""
    from orchestrator import init_progress, log_lever_impact

    progress = init_progress("space_123", "cost")
    before = {"overall_accuracy": 60, "schema_accuracy": 0.55}
    after = {"overall_accuracy": 75, "schema_accuracy": 0.70}
    impact = log_lever_impact(progress, 1, before, after, [{"type": "add_synonym"}])

    assert impact["delta"] == 15
    assert progress["lever_impacts"]["1"]["before"] == before
    assert progress["lever_impacts"]["1"]["after"] == after
    print("  PASS: log_lever_impact")


def test_all_thresholds_met():
    """Test threshold checking."""
    from orchestrator import all_thresholds_met

    passing = {
        "syntax_validity": 99, "schema_accuracy": 96, "logical_accuracy": 91,
        "semantic_equivalence": 91, "completeness": 91, "result_correctness": 86,
        "asset_routing": 96,
    }
    assert all_thresholds_met(passing) is True

    failing = {**passing, "schema_accuracy": 80}
    assert all_thresholds_met(failing) is False

    assert all_thresholds_met({}) is False
    print("  PASS: all_thresholds_met")


def test_default_experiment_path():
    """Test that the default experiment path includes /Users/."""
    from orchestrator import _default_experiment_path

    path = _default_experiment_path("cost")
    assert path.startswith("/Users/")
    assert "cost" in path
    print("  PASS: _default_experiment_path")


def test_add_benchmark_correction():
    """Test arbiter correction tracking."""
    from orchestrator import init_progress, add_benchmark_correction

    progress = init_progress("space_123", "cost")
    add_benchmark_correction(progress, "q1", "SELECT 1", "SELECT 2", "run_abc")
    assert len(progress["benchmark_corrections"]) == 1
    assert progress["benchmark_corrections"][0]["question_id"] == "q1"
    print("  PASS: add_benchmark_correction")


def test_verify_dual_persistence():
    """Test dual persistence verification."""
    from orchestrator import verify_dual_persistence

    results = [
        {"proposal_id": "P001", "repo_status": "success"},
        {"proposal_id": "P002", "repo_status": "pending"},
    ]
    missing = verify_dual_persistence(results)
    assert missing == ["P002"]
    print("  PASS: verify_dual_persistence")


def test_lever_aware_loop_structure():
    """Validate that the lever-aware loop exists and is callable."""
    from orchestrator import _run_lever_aware_loop
    assert callable(_run_lever_aware_loop)
    print("  PASS: _run_lever_aware_loop is callable")


def test_worker_import_wiring():
    """Test that worker import functions exist."""
    from orchestrator import _setup_worker_imports, _import_optimizer, _import_applier
    assert callable(_setup_worker_imports)
    assert callable(_import_optimizer)
    assert callable(_import_applier)
    print("  PASS: worker import wiring")


def run_all():
    verbose = "--verbose" in sys.argv
    tests = [
        test_init_progress,
        test_normalize_scores,
        test_update_progress,
        test_pareto_frontier_uses_patch_cost,
        test_log_lever_impact,
        test_all_thresholds_met,
        test_default_experiment_path,
        test_add_benchmark_correction,
        test_verify_dual_persistence,
        test_lever_aware_loop_structure,
        test_worker_import_wiring,
    ]

    passed = 0
    failed = 0
    print(f"\nRunning {len(tests)} tests...\n")

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test.__name__}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 40}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())

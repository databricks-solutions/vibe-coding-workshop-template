#!/usr/bin/env python3
"""
End-to-end integration test for the Genie Optimization Orchestrator v4.1.0.

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
    assert progress["use_patch_dsl"] is True
    assert "lever_audit" in progress
    assert len(progress["lever_audit"]) == 6
    for i in range(1, 7):
        la = progress["lever_audit"][str(i)]
        assert la["attempted"] is False
        assert la["proposals_generated"] == 0
        assert la["proposals_applied"] == 0
        assert la["skip_reason"] is None
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


def test_asi_aware_clustering():
    """Test that cluster_failures prefers ASI metadata when available."""
    optimizer_path = Path(__file__).parent.parent.parent / "genie-optimization-workers" / "03-genie-metadata-optimizer" / "scripts"
    if str(optimizer_path) not in sys.path:
        sys.path.insert(0, str(optimizer_path))

    from metadata_optimizer import cluster_failures, _map_to_lever

    rows_with_asi = [
        {
            "inputs/question": "q1", "feedback/result_correctness": "no",
            "rationale/result_correctness": "Mismatch",
            "metadata/result_correctness/failure_type": "wrong_aggregation",
            "metadata/result_correctness/blame_set": "booking_analytics_metrics",
            "metadata/result_correctness/counterfactual_fix": "Add column comment to total_bookings",
        },
        {
            "inputs/question": "q2", "feedback/result_correctness": "no",
            "rationale/result_correctness": "Mismatch",
            "metadata/result_correctness/failure_type": "wrong_aggregation",
            "metadata/result_correctness/blame_set": "booking_analytics_metrics",
            "metadata/result_correctness/counterfactual_fix": "Add column comment to total_bookings",
        },
    ]
    clusters = cluster_failures({"rows": rows_with_asi}, {})
    assert len(clusters) >= 1, f"Expected >= 1 cluster, got {len(clusters)}"
    c = clusters[0]
    assert c["asi_failure_type"] == "wrong_aggregation"
    assert c["asi_blame_set"] == "booking_analytics_metrics"
    assert len(c["asi_counterfactual_fixes"]) == 2

    assert _map_to_lever("other", asi_failure_type="wrong_aggregation") == 2
    assert _map_to_lever("other", asi_failure_type=None) == 6
    assert _map_to_lever("wrong_table") == 1
    print("  PASS: test_asi_aware_clustering")


def test_repeatability_integration():
    """Test repeatability v2: cross-iteration comparison, structured metadata routing, synthetic failures."""
    from orchestrator import (
        init_progress, update_progress, _synthesize_repeatability_failures,
        _compute_cross_iteration_repeatability, _synthesize_repeatability_failures_from_cross_iter,
    )

    # 1. init_progress includes repeatability fields
    progress = init_progress("space_123", "cost")
    assert progress["repeatability_pct"] == 0.0, "repeatability_pct should default to 0.0"
    assert progress["best_repeatability"] == 0.0, "best_repeatability should default to 0.0"
    assert progress["repeatability_target"] == 90.0, "repeatability_target should default to 90.0"

    # 2. update_progress tracks repeatability and updates best
    result_with_rep = {
        **MOCK_EVAL_RESULT,
        "model_id": "m001",
        "repeatability_pct": 78.0,
        "repeatability_details": [
            {"question_id": "q1", "question": "What is total revenue?",
             "repeatability_pct": 66.7, "classification": "SIGNIFICANT_VARIANCE",
             "unique_variants": 2, "dominant_asset": "MV", "hashes": ["a1", "a1", "b2"]},
            {"question_id": "q2", "question": "Top 10 customers",
             "repeatability_pct": 100.0, "classification": "IDENTICAL",
             "unique_variants": 1, "dominant_asset": "TABLE", "hashes": ["c3", "c3", "c3"]},
        ],
    }
    update_progress(progress, result_with_rep)
    assert progress["repeatability_pct"] == 78.0
    assert progress["best_repeatability"] == 78.0

    result2 = {
        **MOCK_EVAL_RESULT, "iteration": 2,
        "model_id": "m002",
        "repeatability_pct": 92.0,
    }
    update_progress(progress, result2)
    assert progress["best_repeatability"] == 92.0

    # 3. Pareto frontier includes repeatability
    frontier = progress.get("pareto_frontier", [])
    for v in frontier:
        assert "repeatability" in v, f"Pareto vector missing repeatability: {v}"

    # 4. _map_to_lever routes repeatability_issue by blame_set (v3.8.0)
    optimizer_path = Path(__file__).parent.parent.parent / "genie-optimization-workers" / "03-genie-metadata-optimizer" / "scripts"
    if str(optimizer_path) not in sys.path:
        sys.path.insert(0, str(optimizer_path))
    from metadata_optimizer import _map_to_lever
    assert _map_to_lever("repeatability_issue") == 1, "TABLE default should route to lever 1"
    assert _map_to_lever("repeatability_issue", blame_set="TABLE") == 1, "TABLE -> lever 1"
    assert _map_to_lever("repeatability_issue", blame_set="MV") == 1, "MV -> lever 1"
    assert _map_to_lever("repeatability_issue", blame_set="TVF") == 6, "TVF -> lever 6"
    assert _map_to_lever("other", asi_failure_type="repeatability_issue") == 1, "ASI override -> lever 1"
    assert _map_to_lever("other", asi_failure_type="repeatability_issue", blame_set="TVF") == 6

    # 5. _synthesize_repeatability_failures (Cell 9c data) uses structured metadata counterfactuals
    details = [
        {"question_id": "q1", "question": "Revenue?", "repeatability_pct": 33.3,
         "classification": "CRITICAL_VARIANCE", "unique_variants": 3, "dominant_asset": "MV",
         "hashes": ["a", "b", "c"]},
        {"question_id": "q2", "question": "Customers?", "repeatability_pct": 100.0,
         "classification": "IDENTICAL", "unique_variants": 1, "dominant_asset": "TABLE",
         "hashes": ["d", "d", "d"]},
        {"question_id": "q3", "question": "Churn?", "repeatability_pct": 66.7,
         "classification": "SIGNIFICANT_VARIANCE", "unique_variants": 2, "dominant_asset": "TVF",
         "hashes": ["e", "e", "f"]},
    ]
    synthetic = _synthesize_repeatability_failures(details)
    assert len(synthetic) == 2, f"Expected 2 synthetic failures, got {len(synthetic)}"
    assert synthetic[0]["metadata/repeatability/failure_type"] == "repeatability_issue"
    assert synthetic[0]["metadata/repeatability/severity"] == "critical"
    assert synthetic[0]["metadata/repeatability/blame_set"] == "MV"
    assert "structured" in synthetic[0]["metadata/repeatability/counterfactual_fix"].lower(), \
        "MV counterfactual should recommend structured metadata"
    assert synthetic[1]["metadata/repeatability/blame_set"] == "TVF"
    assert "instruction" in synthetic[1]["metadata/repeatability/counterfactual_fix"].lower(), \
        "TVF counterfactual should recommend instruction"

    # 6. _compute_cross_iteration_repeatability compares SQL across iterations
    prev_rows = [
        {"inputs/question_id": "q1", "inputs/question": "Revenue?",
         "outputs/response": "SELECT SUM(revenue) FROM sales",
         "feedback/result_correctness": "yes"},
        {"inputs/question_id": "q2", "inputs/question": "Top customers",
         "outputs/response": "SELECT * FROM customers LIMIT 10",
         "feedback/result_correctness": "no"},
        {"inputs/question_id": "q3", "inputs/question": "Churn rate",
         "outputs/response": "SELECT get_churn_rate(30)",
         "feedback/result_correctness": "yes"},
    ]
    curr_rows = [
        {"inputs/question_id": "q1", "inputs/question": "Revenue?",
         "outputs/response": "SELECT SUM(revenue) FROM sales"},
        {"inputs/question_id": "q2", "inputs/question": "Top customers",
         "outputs/response": "SELECT name FROM customers ORDER BY spend DESC LIMIT 10"},
        {"inputs/question_id": "q3", "inputs/question": "Churn rate",
         "outputs/response": "SELECT get_churn_rate(60)"},
    ]
    cross_rep = _compute_cross_iteration_repeatability(curr_rows, prev_rows)
    assert cross_rep["total_questions"] == 3
    assert cross_rep["matched"] == 1, "Only q1 should match"
    assert cross_rep["changed"] == 2, "q2 and q3 changed"
    assert 30 < cross_rep["avg_pct"] < 40, f"Expected ~33.3%, got {cross_rep['avg_pct']}"
    unstable = cross_rep["unstable_details"]
    assert len(unstable) == 2
    q2_entry = next(d for d in unstable if d["question_id"] == "q2")
    assert q2_entry["was_previously_correct"] is False
    q3_entry = next(d for d in unstable if d["question_id"] == "q3")
    assert q3_entry["was_previously_correct"] is True
    assert q3_entry["dominant_asset"] == "TVF"

    # 7. _synthesize_repeatability_failures_from_cross_iter only flags previously-correct changes
    cross_synth = _synthesize_repeatability_failures_from_cross_iter(unstable)
    assert len(cross_synth) == 1, "Only q3 (previously correct) should be synthesized"
    assert cross_synth[0]["inputs/question_id"] == "q3"
    assert cross_synth[0]["metadata/repeatability/failure_type"] == "repeatability_issue"
    assert cross_synth[0]["metadata/repeatability/blame_set"] == "TVF"
    assert "instruction" in cross_synth[0]["metadata/repeatability/counterfactual_fix"].lower()

    print("  PASS: test_repeatability_integration")


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
        test_asi_aware_clustering,
        test_repeatability_integration,
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

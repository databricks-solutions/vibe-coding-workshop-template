#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
# ]
# ///
"""Standalone UC model registration with score-based gating.

Compares new evaluation scores against the existing UC champion and
registers a new version only if scores improved. Sets the @champion
alias on success.

Usage:
    python register_model.py \
        --model-uri "runs:/abc123/agent" \
        --catalog main \
        --schema my_agent \
        --model-name my_agent_v1 \
        --scores '{"result_correctness": 0.95, "syntax_validity": 1.0}'
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

import mlflow
from mlflow.tracking import MlflowClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_scores(args: argparse.Namespace) -> dict[str, float]:
    """Build scores dict from --scores JSON."""
    if not args.scores:
        return {}
    raw = json.loads(args.scores)
    if not isinstance(raw, dict):
        raise ValueError("--scores must be a JSON object of string -> number")
    return {str(k): float(v) for k, v in raw.items()}


def _fetch_champion_scores(
    client: MlflowClient,
    tracking_client: MlflowClient,
    uc_model_name: str,
    score_keys: frozenset[str],
) -> tuple[dict[str, float], str | None]:
    """Fetch scores from the existing @champion version's source run."""
    try:
        mv = client.get_model_version_by_alias(uc_model_name, "champion")
        if not mv.run_id:
            return {}, str(mv.version)
        run_data = tracking_client.get_run(mv.run_id).data
        scores = {j: float(run_data.metrics.get(j, 0.0)) for j in score_keys}
        return scores, str(mv.version)
    except Exception:
        return {}, None


def _scores_improved(
    new_scores: dict[str, float],
    existing_scores: dict[str, float],
) -> bool:
    """True if the average of new scores (same keys) is >= existing average."""
    if not existing_scores:
        return True
    if not new_scores:
        return True

    new_avg = sum(new_scores.values()) / len(new_scores)
    old_avg = sum(existing_scores.get(k, 0.0) for k in new_scores) / len(new_scores)
    if new_avg < old_avg:
        logger.info("Average score regressed: %.4f < %.4f", new_avg, old_avg)
        return False

    return True


def register_model(
    model_uri: str,
    catalog: str,
    schema: str,
    model_name: str,
    scores: dict[str, float],
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict | None:
    """Register model to UC and promote if scores improved."""
    uc_model_name = f"{catalog}.{schema}.{model_name}"

    mlflow.set_registry_uri("databricks-uc")
    client = MlflowClient(registry_uri="databricks-uc")
    tracking_client = MlflowClient()

    try:
        client.get_registered_model(uc_model_name)
    except Exception:
        logger.info("Creating UC registered model: %s", uc_model_name)
        client.create_registered_model(
            uc_model_name,
            description="Registered via register_model.py",
        )

    score_keys = frozenset(scores.keys())
    existing_scores, prev_version = _fetch_champion_scores(
        client, tracking_client, uc_model_name, score_keys,
    )

    should_promote = force or _scores_improved(scores, existing_scores)

    if dry_run:
        logger.info("DRY RUN — would register %s, promote=%s", uc_model_name, should_promote)
        return {"uc_model_name": uc_model_name, "dry_run": True, "would_promote": should_promote}

    mv = mlflow.register_model(model_uri, uc_model_name)
    version = str(mv.version)
    logger.info("Registered %s version %s", uc_model_name, version)

    for key, value in scores.items():
        client.set_model_version_tag(uc_model_name, version, key, f"{value:.4f}")
    client.set_model_version_tag(uc_model_name, version, "registered_by", "register_model.py")

    if should_promote:
        client.set_registered_model_alias(uc_model_name, "champion", version)
        logger.info("Promoted version %s as @champion", version)
    else:
        logger.info(
            "Version %s NOT promoted (existing champion v%s is better)",
            version, prev_version,
        )

    return {
        "uc_model_name": uc_model_name,
        "version": version,
        "promoted_to_champion": should_promote,
        "previous_champion_version": prev_version,
        "scores": scores,
        "existing_scores": existing_scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Register model to UC with score gating")
    parser.add_argument("--model-uri", required=True, help="MLflow model URI (e.g., runs:/abc/agent)")
    parser.add_argument("--catalog", required=True, help="UC catalog name")
    parser.add_argument("--schema", required=True, help="UC schema name")
    parser.add_argument("--model-name", required=True, help="Model name (without catalog.schema prefix)")
    parser.add_argument(
        "--scores",
        required=True,
        help='JSON object of metric name -> float, e.g. \'{"quality": 0.9, "safety": 1.0}\'',
    )
    parser.add_argument("--force", action="store_true", help="Promote regardless of scores")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without registering")

    args = parser.parse_args()
    try:
        scores = _parse_scores(args)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid --scores JSON: %s", e)
        sys.exit(1)

    if not scores:
        logger.error("No scores provided. Pass a non-empty object via --scores.")
        sys.exit(1)

    result = register_model(
        model_uri=args.model_uri,
        catalog=args.catalog,
        schema=args.schema,
        model_name=args.model_name,
        scores=scores,
        force=args.force,
        dry_run=args.dry_run,
    )

    if result:
        print(json.dumps(result, indent=2, default=str))
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

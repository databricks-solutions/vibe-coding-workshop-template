#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
# ]
# ///
"""Register production scorers for a deployed GenAI agent.

Registers Safety (100%), Correctness (20%), Guidelines (10%), and optional
custom domain scorers, then starts all with the specified sampling rates.
Verifies active scorers via list_scorers().

Usage:
    python register_production_scorers.py --model-name my-agent
    python register_production_scorers.py \
        --model-name my-agent \
        --safety-rate 1.0 \
        --correctness-rate 0.2 \
        --guidelines-rate 0.1 \
        --skip-custom
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass


@dataclass
class ScorerSpec:
    """Specification for a scorer to register."""

    name: str
    sample_rate: float
    scorer_type: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register production scorers for a deployed model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --model-name my-agent\n"
            "  %(prog)s --model-name my-agent --safety-rate 1.0 --correctness-rate 0.15\n"
            "  %(prog)s --model-name my-agent --prefix staging --skip-custom\n"
        ),
    )
    parser.add_argument(
        "--model-name",
        required=True,
        help="MLflow registered model or serving endpoint name",
    )
    parser.add_argument(
        "--prefix",
        default="prod",
        help="Scorer name prefix for environment namespacing (default: prod)",
    )
    parser.add_argument(
        "--safety-rate",
        type=float,
        default=1.0,
        help="Sample rate for Safety scorer (default: 1.0)",
    )
    parser.add_argument(
        "--correctness-rate",
        type=float,
        default=0.2,
        help="Sample rate for Correctness scorer (default: 0.2)",
    )
    parser.add_argument(
        "--guidelines-rate",
        type=float,
        default=0.1,
        help="Sample rate for Guidelines scorer (default: 0.1)",
    )
    parser.add_argument(
        "--skip-custom",
        action="store_true",
        help="Skip registering custom domain scorers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be registered without actually registering",
    )
    return parser.parse_args()


def register_builtin_scorers(
    model_name: str,
    prefix: str,
    safety_rate: float,
    correctness_rate: float,
    guidelines_rate: float,
    dry_run: bool,
) -> list[ScorerSpec]:
    """Register and start built-in MLflow GenAI scorers."""
    from mlflow.genai import ScorerSamplingConfig
    from mlflow.genai.scorers import Correctness, Guidelines, Safety

    specs = [
        ScorerSpec(f"{prefix}_safety", safety_rate, "Safety", "Policy violation detection"),
        ScorerSpec(f"{prefix}_correctness", correctness_rate, "Correctness", "Factual accuracy judge"),
        ScorerSpec(f"{prefix}_guidelines", guidelines_rate, "Guidelines", "Professional tone enforcement"),
    ]

    if dry_run:
        for s in specs:
            print(f"  [DRY RUN] Would register {s.name} ({s.scorer_type}) at {s.sample_rate:.0%}")
        return specs

    scorers_map = {
        f"{prefix}_safety": Safety(),
        f"{prefix}_correctness": Correctness(),
        f"{prefix}_guidelines": Guidelines(
            name="professional_tone",
            guidelines=(
                "Responses must be professional, concise, and directly address "
                "the user's question. Avoid jargon unless the user is technical."
            ),
        ),
    }

    registered = []
    for spec in specs:
        raw = scorers_map[spec.name]
        try:
            s = raw.register(name=spec.name, model_name=model_name)
            s = s.start(sampling_config=ScorerSamplingConfig(sample_rate=spec.sample_rate))
            print(f"  ✓ {spec.name} ({spec.scorer_type}) — {spec.sample_rate:.0%} sampling")
            registered.append(spec)
        except Exception as e:
            print(f"  ✗ {spec.name} FAILED: {e}", file=sys.stderr)

    return registered


def register_custom_scorers(
    model_name: str,
    prefix: str,
    dry_run: bool,
) -> list[ScorerSpec]:
    """Register and start custom domain-specific scorers."""
    from mlflow.genai import ScorerSamplingConfig, scorer

    specs = [
        ScorerSpec(f"{prefix}_sql_syntax", 0.5, "Custom", "SQL syntax validation"),
        ScorerSpec(f"{prefix}_response_length", 1.0, "Custom", "Response length guard"),
    ]

    if dry_run:
        for s in specs:
            print(f"  [DRY RUN] Would register {s.name} ({s.description}) at {s.sample_rate:.0%}")
        return specs

    @scorer
    def sql_syntax_check(inputs: dict, outputs: dict) -> float:
        sql = (outputs.get("generated_sql") or "").strip()
        if not sql:
            return 1.0
        upper = sql.upper()
        if not any(upper.startswith(k) for k in ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "MERGE")):
            return 0.0
        return 1.0

    @scorer
    def response_length_guard(inputs: dict, outputs: dict) -> float:
        text = outputs.get("response", "")
        length = len(text)
        if length > 5000 or length < 10:
            return 0.0
        return 1.0

    custom_scorers = {
        f"{prefix}_sql_syntax": (sql_syntax_check, 0.5),
        f"{prefix}_response_length": (response_length_guard, 1.0),
    }

    registered = []
    for spec in specs:
        fn, rate = custom_scorers[spec.name]
        try:
            s = fn.register(name=spec.name, model_name=model_name)
            s = s.start(sampling_config=ScorerSamplingConfig(sample_rate=rate))
            print(f"  ✓ {spec.name} ({spec.description}) — {rate:.0%} sampling")
            registered.append(spec)
        except Exception as e:
            print(f"  ✗ {spec.name} FAILED: {e}", file=sys.stderr)

    return registered


def verify_scorers(model_name: str, prefix: str) -> list[dict[str, str]]:
    """List active scorers whose names match the prefix filter."""
    from mlflow.genai.scorers import list_scorers

    print("\nActive scorers (name prefix filter):")
    print("-" * 60)
    scorers = list_scorers()
    relevant = [s for s in scorers if s.name.startswith(prefix)]

    rows: list[dict[str, str]] = []
    if not relevant:
        print(f"  ⚠ No scorers found with name starting with '{prefix}'")
        return rows

    for s in relevant:
        status = getattr(s, "status", "")
        print(f"  {s.name:40s} status={status}")
        rows.append({"name": s.name, "status": str(status)})
    print(f"\nTotal: {len(relevant)} scorer(s) matching prefix '{prefix}' (model: {model_name})")
    return rows


def main() -> None:
    args = parse_args()

    print(f"Model: {args.model_name}")
    print(f"Prefix: {args.prefix}")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)\n")
    print()

    print("Registering built-in scorers...")
    builtin = register_builtin_scorers(
        model_name=args.model_name,
        prefix=args.prefix,
        safety_rate=args.safety_rate,
        correctness_rate=args.correctness_rate,
        guidelines_rate=args.guidelines_rate,
        dry_run=args.dry_run,
    )

    custom: list[ScorerSpec] = []
    if not args.skip_custom:
        print("\nRegistering custom domain scorers...")
        custom = register_custom_scorers(
            model_name=args.model_name,
            prefix=args.prefix,
            dry_run=args.dry_run,
        )
    else:
        print("\nSkipping custom scorers (--skip-custom)")

    total = len(builtin) + len(custom)
    print(f"\nRegistered {total} scorer(s)")

    verification: list[dict[str, str]] = []
    if not args.dry_run:
        verification = verify_scorers(args.model_name, args.prefix)

    summary = {
        "model_name": args.model_name,
        "prefix": args.prefix,
        "dry_run": args.dry_run,
        "builtin_registered": len(builtin),
        "custom_registered": len(custom),
        "total_registered_specs": total,
        "builtin_names": [s.name for s in builtin],
        "custom_names": [s.name for s in custom],
        "verification_scorers": verification,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

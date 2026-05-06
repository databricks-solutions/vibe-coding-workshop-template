#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mlflow[databricks]>=3.10",
# ]
# ///
"""Register a prompt to the MLflow Prompt Registry under Unity Catalog.

Standalone script that:
  1. Sets the MLflow experiment with the promptRegistryLocation tag.
  2. Registers the prompt with a UC-qualified three-level name.
  3. Sets the ``production`` alias on the new version.
  4. Verifies by loading the prompt back via the alias.

Usage:
    python register_prompts.py \
        --catalog main \
        --schema my_agent \
        --prompt-name syntax_validity \
        --template-text "Score this SQL: {{ sql_text }}"

    python register_prompts.py \
        --catalog main \
        --schema my_agent \
        --prompt-name syntax_validity \
        --template-file ./prompts/syntax_judge.txt \
        --alias staging \
        --experiment /Users/<user_email>/mlflow/<APP_NAME>-prompts \
        --commit-message "Stricter scoring rubric v2"

The --experiment path MUST be the user-and-use-case-pinned path
(e.g. /Users/jane.doe@example.com/mlflow/jane-d-stayfinder-prompts).
Read it from .vibecoding-state.md (mlflow_experiment_path with the leaf
swapped from -agent to -prompts) instead of using a literal placeholder.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import mlflow
import mlflow.genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_EXPERIMENT: str | None = None
DEFAULT_ALIAS = "production"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register a prompt in the MLflow Prompt Registry (UC-backed).",
    )
    parser.add_argument(
        "--catalog",
        required=True,
        help="Unity Catalog catalog name (e.g. 'main').",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Unity Catalog schema name (e.g. 'my_agent').",
    )
    parser.add_argument(
        "--prompt-name",
        required=True,
        help="Short prompt identifier (e.g. 'syntax_validity'). "
        "Will be prefixed with catalog.schema automatically.",
    )

    template_group = parser.add_mutually_exclusive_group(required=True)
    template_group.add_argument(
        "--template-text",
        help="Inline template string with {{ variable }} placeholders.",
    )
    template_group.add_argument(
        "--template-file",
        type=Path,
        help="Path to a file containing the template text.",
    )

    parser.add_argument(
        "--alias",
        default=DEFAULT_ALIAS,
        help=f"Alias to set on the new version (default: {DEFAULT_ALIAS}).",
    )
    parser.add_argument(
        "--experiment",
        default=DEFAULT_EXPERIMENT,
        required=DEFAULT_EXPERIMENT is None,
        help=(
            "MLflow experiment path. Required — pass the user-and-use-case-pinned "
            "path /Users/<user_email>/mlflow/<APP_NAME>-prompts "
            "(e.g. /Users/jane.doe@example.com/mlflow/jane-d-stayfinder-prompts) "
            "so the prompt registry never lands in a generic /Shared/Tracing-style "
            "experiment shared across attendees."
        ),
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Commit message for the prompt version. "
        "Defaults to 'Registered via register_prompts.py'.",
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        metavar="KEY=VALUE",
        help="Extra tags as key=value pairs (e.g. --tags domain=sales type=judge).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without registering.",
    )
    return parser.parse_args(argv)


def _parse_tags(raw: list[str] | None) -> dict[str, str]:
    tags: dict[str, str] = {}
    for item in raw or []:
        if "=" not in item:
            logger.warning("Skipping malformed tag (expected KEY=VALUE): %s", item)
            continue
        key, value = item.split("=", 1)
        tags[key.strip()] = value.strip()
    return tags


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    uc_schema = f"{args.catalog}.{args.schema}"
    fqn = f"{uc_schema}.{args.prompt_name}"
    alias = args.alias
    commit_msg = args.commit_message or "Registered via register_prompts.py"
    extra_tags = _parse_tags(args.tags)

    if args.template_file:
        if not args.template_file.exists():
            logger.error("Template file not found: %s", args.template_file)
            return 1
        template_text = args.template_file.read_text(encoding="utf-8")
    else:
        template_text = args.template_text

    if not template_text or not template_text.strip():
        logger.error("Template text is empty.")
        return 1

    logger.info("Prompt FQN:    %s", fqn)
    logger.info("Alias:         @%s", alias)
    logger.info("Experiment:    %s", args.experiment)
    logger.info("Template:      %s...", template_text[:80].replace("\n", "\\n"))
    if extra_tags:
        logger.info("Extra tags:    %s", extra_tags)

    if args.dry_run:
        logger.info("[DRY RUN] Would register prompt — exiting.")
        return 0

    # Step 1: Set experiment and tag
    logger.info("Setting experiment: %s", args.experiment)
    mlflow.set_experiment(args.experiment)

    try:
        mlflow.set_experiment_tags({
            "mlflow.promptRegistryLocation": uc_schema,
        })
        logger.info("Set promptRegistryLocation tag to %s", uc_schema)
    except Exception:
        logger.warning(
            "Failed to set promptRegistryLocation tag (non-fatal)", exc_info=True,
        )

    # Step 2: Register prompt
    logger.info("Registering prompt: %s", fqn)
    try:
        version = mlflow.genai.register_prompt(
            name=fqn,
            template=template_text,
            commit_message=commit_msg,
            tags=extra_tags,
        )
    except Exception:
        logger.exception("Failed to register prompt %s", fqn)
        return 1

    logger.info("Registered %s version %s", fqn, version.version)

    # Step 3: Set alias
    logger.info("Setting alias @%s → version %s", alias, version.version)
    try:
        mlflow.genai.set_prompt_alias(
            name=fqn,
            alias=alias,
            version=version.version,
        )
    except Exception:
        logger.exception("Failed to set alias @%s on %s", alias, fqn)
        return 1

    logger.info("Alias @%s set successfully", alias)

    # Step 4: Verify by loading
    logger.info("Verifying: loading prompts:/%s@%s", fqn, alias)
    try:
        loaded = mlflow.genai.load_prompt(f"prompts:/{fqn}@{alias}")
        assert loaded.template is not None, "Loaded template is None"
        logger.info(
            "Verified: version %s, template length %d chars",
            loaded.version,
            len(loaded.template),
        )
    except Exception:
        logger.exception("Verification failed — prompt may not be loadable")
        return 1

    logger.info("Done. Prompt %s@%s is ready.", fqn, alias)
    print(json.dumps({
        "prompt_name": fqn,
        "version": version.version,
        "alias": alias,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

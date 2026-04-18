"""
Shared helper for resolving Asset Bundle paths inside Databricks notebooks.

This module is the canonical, skill-defect-free implementation of:

  1. Resolving the Asset Bundle ROOT from the current notebook path.
  2. Prepending it to sys.path so `from src.xxx import yyy` works.
  3. Loading files (YAML / JSON / text) with BOTH notebook-context and
     job-context-safe paths — never relying on ``__file__`` (which is
     undefined in notebook cells).

Copy this file verbatim into any Databricks notebook project that needs
to share code or load bundle-relative asset files. Do NOT edit the
`resolve_bundle_root` logic — the ``rsplit('/src/', 1)[0]`` pattern is
project-invariant, while any ``.replace('/src/<hardcoded_project>', '')``
variant is the #1 failure mode observed in production.

See: data_product_accelerator/skills/common/databricks-python-imports/SKILL.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _get_dbutils():
    """Return dbutils if we are inside a Databricks notebook, else None."""
    try:
        # Injected into the notebook global namespace by Databricks.
        return globals().get("dbutils") or locals().get("dbutils")  # type: ignore[name-defined]
    except Exception:
        return None


def resolve_bundle_root(verbose: bool = False) -> Optional[str]:
    """
    Resolve the Databricks Asset Bundle root directory.

    Resolution order:
      1. ``BUNDLE_ROOT`` env var (honours explicit override; test injection).
      2. Notebook context via dbutils — the canonical production path.
         Splits on ``/src/`` to handle ANY project name without hard-coding.
      3. ``None`` — caller should fall back to CWD/local execution.

    NEVER raises. Callers must handle the ``None`` case explicitly (usually
    by no-op'ing sys.path setup for local / non-bundle execution).

    Returns:
        The ``/Workspace``-prefixed absolute bundle root, or ``None``.
    """
    override = os.environ.get("BUNDLE_ROOT")
    if override:
        if verbose:
            print(f"✓ bundle_root from BUNDLE_ROOT env: {override}")
        return override

    dbu = _get_dbutils()
    if dbu is None:
        return None
    try:
        notebook_path = (
            dbu.notebook.entry_point.getDbutils()
            .notebook()
            .getContext()
            .notebookPath()
            .get()
        )
        if not notebook_path:
            return None
        # Canonical pattern — works for ANY project under /src/.
        bundle_root = "/Workspace" + str(notebook_path).rsplit("/src/", 1)[0]
        if verbose:
            print(f"✓ bundle_root resolved from notebook path: {bundle_root}")
        return bundle_root
    except Exception as e:
        if verbose:
            print(f"⚠ bundle_root resolution skipped (local execution?): {e}")
        return None


def ensure_bundle_root_on_path(verbose: bool = True) -> Optional[str]:
    """
    Resolve the bundle root AND prepend it to ``sys.path`` if present.

    Idempotent — safe to call multiple times. Returns the resolved root
    (or ``None`` for local execution) so the caller can also use it for
    asset file loading via :func:`bundle_path`.
    """
    root = resolve_bundle_root(verbose=verbose)
    if root and root not in sys.path:
        sys.path.insert(0, root)
        if verbose:
            print(f"✓ Added bundle root to sys.path: {root}")
    return root


def bundle_path(*parts: str) -> Path:
    """
    Build an absolute path relative to the bundle root.

    Example::

        cfg_path = bundle_path("src", "semantic", "metric_views", "revenue.yaml")
        data = yaml.safe_load(cfg_path.read_text())

    Falls back to the current working directory when no bundle root is
    resolvable (local script execution). This matches the intent of
    ``--yaml-dir src/...`` style relative arguments passed via widgets.
    """
    root = resolve_bundle_root(verbose=False)
    if root:
        return Path(root, *parts)
    # Local execution — use CWD as the root.
    return Path(*parts).resolve()


def fail_loud(msg: str) -> None:
    """
    Fail the job visibly. NEVER use ``sys.exit(0)`` to report failure — a
    zero exit is interpreted as success by Databricks Jobs and silently
    masks broken deploys. Always raise so the job run is marked FAILED
    and the traceback appears in the run's driver logs.
    """
    raise RuntimeError(msg)


__all__ = [
    "resolve_bundle_root",
    "ensure_bundle_root_on_path",
    "bundle_path",
    "fail_loud",
]

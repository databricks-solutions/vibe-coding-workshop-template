# Experiment Organization — Complete Reference

> **Skill:** 01-experiment-tracing-setup
> **Grounded in:** `src/genie_space_optimizer/common/config.py` —
> `EXPERIMENT_PATH_TEMPLATE`, `format_mlflow_template()`

---

## 1. Path Template Mechanics

The project defines a single canonical template for all experiment paths:

```python
# src/genie_space_optimizer/common/config.py  (section 13)
EXPERIMENT_PATH_TEMPLATE = "/Shared/genie-space-optimizer/{{ space_id }}/{{ domain }}"
```

Placeholders use double-brace `{{ key }}` syntax — **not** Python `str.format()`
— because `format_mlflow_template()` intentionally leaves missing keys intact
for partial-formatting scenarios.

### `format_mlflow_template` implementation

```python
import re
from typing import Any


def format_mlflow_template(template: str, **kwargs: Any) -> str:
    """Format a template that uses MLflow's ``{{ variable }}`` syntax.

    Unlike Python's ``str.format()``, single braces are treated as literal
    characters and ``{{ variable }}`` is the interpolation marker.
    Missing keys are left as-is so partial formatting is safe.
    """

    def _replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in kwargs:
            return str(kwargs[key])
        return match.group(0)

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replacer, template)
```

### Usage patterns

```python
from genie_space_optimizer.common.config import (
    EXPERIMENT_PATH_TEMPLATE,
    format_mlflow_template,
)

# Full resolution — all keys supplied
path = format_mlflow_template(
    EXPERIMENT_PATH_TEMPLATE,
    space_id="abc123",
    domain="billing",
)
# → "/Shared/genie-space-optimizer/abc123/billing"

# Partial resolution — domain left for later
partial = format_mlflow_template(EXPERIMENT_PATH_TEMPLATE, space_id="abc123")
# → "/Shared/genie-space-optimizer/abc123/{{ domain }}"
```

---

## 2. Three-Experiment Lifecycle Pattern

Multi-stage GenAI pipelines should separate concerns into distinct experiments
so that development noise, evaluation benchmarks, and deployment artifacts are
never interleaved.

| Stage      | `domain` value | Purpose                                              |
| ---------- | -------------- | ---------------------------------------------------- |
| **dev**    | `dev`          | Interactive debugging, short runs, permissive logging |
| **eval**   | `eval`         | Benchmarks, `mlflow.genai.evaluate`, regression gates |
| **deploy** | `deploy`       | Production runs, stricter tags and retention policies |

### Complete setup function

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import mlflow

from genie_space_optimizer.common.config import (
    EXPERIMENT_PATH_TEMPLATE,
    format_mlflow_template,
)

logger = logging.getLogger(__name__)


@dataclass
class ExperimentPaths:
    """Resolved experiment paths for all lifecycle stages."""

    dev: str
    eval: str
    deploy: str

    @classmethod
    def from_space(cls, space_id: str) -> "ExperimentPaths":
        """Build paths for a single Genie Space across all stages."""
        return cls(
            dev=format_mlflow_template(
                EXPERIMENT_PATH_TEMPLATE, space_id=space_id, domain="dev"
            ),
            eval=format_mlflow_template(
                EXPERIMENT_PATH_TEMPLATE, space_id=space_id, domain="eval"
            ),
            deploy=format_mlflow_template(
                EXPERIMENT_PATH_TEMPLATE, space_id=space_id, domain="deploy"
            ),
        )


def setup_experiment_for_stage(
    space_id: str,
    stage: str,
    *,
    catalog: str | None = None,
    schema: str | None = None,
    extra_tags: dict[str, str] | None = None,
) -> str:
    """Resolve the experiment path, create/set it, and apply standard tags.

    Args:
        space_id: Genie Space identifier.
        stage: One of ``dev``, ``eval``, ``deploy``.
        catalog: Unity Catalog name for prompt registry linkage.
        schema: UC schema name for prompt registry linkage.
        extra_tags: Additional experiment-level tags.

    Returns:
        The resolved experiment path.
    """
    paths = ExperimentPaths.from_space(space_id)
    exp_path = getattr(paths, stage)

    mlflow.set_experiment(exp_path)

    tags: dict[str, str] = {}
    if catalog and schema:
        tags["mlflow.promptRegistryLocation"] = f"{catalog}.{schema}"
    if extra_tags:
        tags.update(extra_tags)
    if tags:
        mlflow.set_experiment_tags(tags)

    logger.info("Experiment set: %s (stage=%s, tags=%s)", exp_path, stage, list(tags))
    return exp_path
```

---

## 3. ExperimentManager Helper Class

A higher-level manager that wraps creation, tagging, and search into a
cohesive interface.

```python
from __future__ import annotations

import logging
from typing import Any

import mlflow
from mlflow.entities import Experiment
from mlflow.tracking import MlflowClient

from genie_space_optimizer.common.config import (
    EXPERIMENT_PATH_TEMPLATE,
    format_mlflow_template,
)

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Manage MLflow experiments with structured path conventions.

    Encapsulates the three-experiment lifecycle pattern and provides
    helpers for tagging, search, and cleanup.
    """

    def __init__(self, client: MlflowClient | None = None) -> None:
        self._client = client or MlflowClient()

    def create_or_get_experiment(
        self,
        space_id: str,
        domain: str,
        *,
        tags: dict[str, str] | None = None,
    ) -> Experiment:
        """Create the experiment if it does not exist, otherwise return it.

        Args:
            space_id: Genie Space identifier.
            domain: Pipeline stage or functional domain (``dev``, ``eval``, etc.).
            tags: Experiment-level tags to set or update.

        Returns:
            The ``Experiment`` object (existing or newly created).
        """
        path = format_mlflow_template(
            EXPERIMENT_PATH_TEMPLATE, space_id=space_id, domain=domain
        )
        exp = self._client.get_experiment_by_name(path)
        if exp is None:
            exp_id = self._client.create_experiment(path, tags=tags or {})
            exp = self._client.get_experiment(exp_id)
            logger.info("Created experiment: %s (id=%s)", path, exp_id)
        else:
            if tags:
                for key, value in tags.items():
                    self._client.set_experiment_tag(exp.experiment_id, key, value)
            logger.info("Reusing experiment: %s (id=%s)", path, exp.experiment_id)
        return exp

    def tag_for_prompt_registry(
        self,
        experiment_id: str,
        catalog: str,
        schema: str,
    ) -> None:
        """Link an experiment to a Unity Catalog prompt registry location.

        This tag makes UC-registered prompts visible in the MLflow Experiment
        UI for prompt-aware workflows.

        Args:
            experiment_id: MLflow experiment ID.
            catalog: Unity Catalog name.
            schema: UC schema name.
        """
        location = f"{catalog}.{schema}"
        self._client.set_experiment_tag(
            experiment_id, "mlflow.promptRegistryLocation", location
        )
        logger.info(
            "Experiment %s linked to prompt registry: %s",
            experiment_id,
            location,
        )

    def list_experiments_for_domain(
        self,
        domain: str,
        *,
        max_results: int = 100,
    ) -> list[Experiment]:
        """Search experiments matching a domain path segment.

        Searches for experiments whose name contains the domain string
        within the standard path structure.

        Args:
            domain: Domain or stage to search for (e.g. ``eval``).
            max_results: Maximum number of experiments to return.

        Returns:
            List of matching ``Experiment`` objects.
        """
        filter_str = f"name LIKE '%/genie-space-optimizer/%/{domain}'"
        results = self._client.search_experiments(
            filter_string=filter_str,
            max_results=max_results,
        )
        return list(results)

    def cleanup_stale_experiments(
        self,
        domain: str,
        *,
        older_than_days: int = 90,
        dry_run: bool = True,
    ) -> list[str]:
        """Identify experiments with no recent runs for cleanup.

        Args:
            domain: Domain to scan.
            older_than_days: Threshold for staleness.
            dry_run: If True, only report — do not delete.

        Returns:
            List of experiment paths that are stale (or were deleted).
        """
        import time

        cutoff_ms = int((time.time() - older_than_days * 86400) * 1000)
        experiments = self.list_experiments_for_domain(domain)
        stale: list[str] = []

        for exp in experiments:
            runs = self._client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1,
                order_by=["start_time DESC"],
            )
            if not runs or runs[0].info.start_time < cutoff_ms:
                stale.append(exp.name)
                if not dry_run:
                    self._client.delete_experiment(exp.experiment_id)
                    logger.warning("Deleted stale experiment: %s", exp.name)

        logger.info(
            "Stale experiments for domain=%s: %d (dry_run=%s)",
            domain,
            len(stale),
            dry_run,
        )
        return stale
```

---

## 4. Experiment Tagging Strategies

### Standard tags set by this project

| Tag key                            | Set by                   | Purpose                                   |
| ---------------------------------- | ------------------------ | ----------------------------------------- |
| `mlflow.promptRegistryLocation`    | `evaluation.py`          | Links UC prompt registry to experiment UI  |
| `genie.space_id`                   | `preflight.py`           | Space-level filtering                      |
| `genie.domain`                     | `preflight.py`           | Domain segmentation                        |
| `genie.pipeline_version`           | `preflight.py`           | Correlate runs with code version           |
| `genie.catalog`                    | `preflight.py`           | Unity Catalog name for audit               |
| `genie.schema`                     | `preflight.py`           | UC schema for audit                        |

### Custom tags for your organization

```python
mlflow.set_experiment_tags({
    "team": "data-platform",
    "project": "genie-optimizer",
    "cost_center": "eng-ml",
    "sla_tier": "gold",
})
```

---

## 5. Decision Table — Create New vs Reuse Experiments

| Scenario                                 | Action                  | Rationale                                           |
| ---------------------------------------- | ----------------------- | --------------------------------------------------- |
| New Genie Space being optimized          | **Create new**          | Unique `space_id` in path keeps runs isolated        |
| Re-running eval for same space + domain  | **Reuse existing**      | Runs accumulate under the same experiment for trends |
| Switching from dev to eval               | **Create new** (stage)  | Separate lifecycle stage = separate experiment       |
| Code version bump (same space + stage)   | **Reuse existing**      | Tag with `genie.pipeline_version` instead            |
| Entirely new team or project             | **New template**        | Fork `EXPERIMENT_PATH_TEMPLATE` with a new prefix    |
| Temporary debugging run                  | **Reuse dev experiment**| Dev experiment tolerates noisy runs                  |

---

## 6. Experiment Search Patterns

### Search by tag

```python
client = MlflowClient()

experiments = client.search_experiments(
    filter_string="tags.`genie.space_id` = 'abc123'",
    max_results=10,
)
```

### Search runs within an experiment

```python
runs = client.search_runs(
    experiment_ids=[exp.experiment_id],
    filter_string="tags.`genie.pipeline_version` = '2.1.0'",
    order_by=["metrics.result_correctness DESC"],
    max_results=5,
)
```

### Search across all experiments by name pattern

```python
eval_experiments = client.search_experiments(
    filter_string="name LIKE '/Shared/genie-space-optimizer/%/eval'",
)
```

---

## 7. Integration with Other Config Templates

The experiment template sits alongside other MLflow naming conventions in
`config.py` section 13:

```python
EXPERIMENT_PATH_TEMPLATE = "/Shared/genie-space-optimizer/{{ space_id }}/{{ domain }}"
RUN_NAME_TEMPLATE        = "iter_{{ iteration }}_eval_{{ timestamp }}"
BASELINE_RUN_NAME_TEMPLATE = "baseline_eval_{{ timestamp }}"
MODEL_NAME_TEMPLATE      = "genie-space-{{ space_id }}"
UC_REGISTERED_MODEL_TEMPLATE = "{{ catalog }}.{{ schema }}.genie_space_{{ space_id }}"
```

All use `format_mlflow_template()` for consistent interpolation. Adjust templates
if your organization requires a different workspace path prefix (e.g.
`/Users/<user>/` instead of `/Shared/`).

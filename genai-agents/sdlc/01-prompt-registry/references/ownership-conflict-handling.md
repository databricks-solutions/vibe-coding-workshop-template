# Ownership Conflict Handling for Prompt Registration

> Complete reference for diagnosing and recovering from prompt registration
> failures caused by ownership conflicts, permission boundaries, and
> missing resources in the MLflow Prompt Registry.

---

## Why Conflicts Occur

Prompts in Unity Catalog are stored as **UC functions**. Each function has
an **owner** — the principal that created it. Only the owner (or a principal
with `MANAGE` privilege on the schema) can update the function.

Conflicts arise when:

| Scenario | Root cause |
|----------|-----------|
| **Multi-user registration** | Developer A creates the prompt; Developer B's service principal tries to register a new version. B is not the owner. |
| **Service principal rotation** | The Databricks App is redeployed with a new SP, but the old SP still owns existing prompts. |
| **Shared schema, separate teams** | Two teams register prompts in the same schema with different SPs. |
| **Dev → Prod migration** | A prompt created in dev (by a personal token) is re-registered in prod (by a job SP). |
| **Re-creation after delete** | A prompt was deleted and re-created by a different principal, changing ownership. |

The MLflow error typically looks like:

```
PERMISSION_DENIED: User does not have permission to update prompt
'main.genie_optimization.genie_opt_syntax_validity'
```

---

## Error Classification

The `_classify_prompt_registration_error()` function in `evaluation.py`
(lines 2002–2057) classifies registration failures into actionable buckets:

### Classification Buckets

| Reason | Detection markers | Remediation |
|--------|------------------|-------------|
| `missing_uc_permissions` | "permission", "privilege", "not authorized", "forbidden", "insufficient", "access denied", "permission_denied" | Grant `CREATE FUNCTION`, `EXECUTE`, `MANAGE` on the target schema |
| `feature_not_enabled` | "preview" + ("prompt" or "genai") | Enable MLflow Prompt Registry in workspace settings |
| `registry_path_not_found` | "does not exist", "resource_does_not_exist" | Verify catalog/schema exists and is accessible |
| `unknown` | None of the above | Inspect full stack trace |

### Implementation

```python
from typing import Any

PROMPT_REGISTRY_REQUIRED_PRIVILEGES = ("CREATE FUNCTION", "EXECUTE", "MANAGE")


def _classify_prompt_registration_error(
    message: str, uc_schema: str
) -> dict[str, Any]:
    """Classify prompt registration failure into actionable root-cause buckets."""
    lowered = (message or "").lower()
    permission_markers = (
        "permission",
        "privilege",
        "not authorized",
        "forbidden",
        "insufficient",
        "access denied",
        "permission_denied",
    )
    missing_privileges = [
        priv
        for priv in PROMPT_REGISTRY_REQUIRED_PRIVILEGES
        if priv.lower() in lowered
    ]

    if any(marker in lowered for marker in permission_markers):
        if not missing_privileges:
            missing_privileges = list(PROMPT_REGISTRY_REQUIRED_PRIVILEGES)
        schema_target = uc_schema or "<catalog>.<schema>"
        return {
            "reason": "missing_uc_permissions",
            "missing_privileges": missing_privileges,
            "remediation": (
                f"Grant {', '.join(missing_privileges)} on schema "
                f"{schema_target} to the Databricks App service principal "
                "used by job tasks."
            ),
        }

    if "preview" in lowered and ("prompt" in lowered or "genai" in lowered):
        return {
            "reason": "feature_not_enabled",
            "missing_privileges": [],
            "remediation": (
                "Enable MLflow Prompt Registry / GenAI preview in "
                "workspace settings."
            ),
        }

    if "does not exist" in lowered or "resource_does_not_exist" in lowered:
        schema_target = uc_schema or "<catalog>.<schema>"
        return {
            "reason": "registry_path_not_found",
            "missing_privileges": [],
            "remediation": (
                f"Verify catalog/schema exists and is accessible: "
                f"{schema_target}."
            ),
        }

    return {
        "reason": "unknown",
        "missing_privileges": [],
        "remediation": (
            "Inspect full stack trace for prompt registration failure "
            "details and verify Prompt Registry availability."
        ),
    }
```

---

## Ownership Conflict Detection

The `_is_ownership_conflict()` function (line 1976) detects whether the
error is specifically an ownership mismatch (not a broader permission issue):

```python
def _is_ownership_conflict(err_msg: str) -> bool:
    """True when MLflow can't update an existing prompt due to ownership mismatch."""
    lowered = (err_msg or "").lower()
    return "permission_denied" in lowered and "update prompt" in lowered
```

This is a narrower check than `_classify_prompt_registration_error` — it
specifically targets the "update prompt" error that indicates the function
exists but is owned by someone else.

---

## Recovery: Drop and Re-Create

When an ownership conflict is detected, the codebase attempts to **drop**
the stale function and re-create it under the current principal's ownership:

```python
import logging

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


def _try_drop_prompt(fqn: str) -> bool:
    """Best-effort drop of a stale prompt (UC function) so it can be re-created.

    Returns True if the drop succeeded (or the function didn't exist).
    """
    if "." not in fqn:
        return False
    try:
        w = WorkspaceClient()
        w.functions.delete(fqn)
        logger.info("Dropped stale prompt function %s", fqn)
        return True
    except Exception:
        logger.debug("Could not drop stale prompt %s", fqn, exc_info=True)
        return False
```

**Important:** The drop requires the current principal to have `MANAGE` on
the schema (or ownership of the function). If the principal lacks these
privileges, the drop fails silently and the next fallback candidate is tried.

---

## `_prompt_name_candidates()` Fallback Strategy

When registration of the primary name fails (for any reason), the system
tries alternative names. This is the core resilience mechanism grounded in
`evaluation.py` lines 2549–2557:

```python
import re

from genie_space_optimizer.common.config import (
    PROMPT_NAME_TEMPLATE,
    format_mlflow_template,
)


def _prompt_name_candidates(
    uc_schema: str, domain: str, judge_name: str
) -> list[str]:
    """Try UC-qualified name first, then portable fallback names."""
    safe_domain = (
        re.sub(r"[^a-zA-Z0-9_]+", "_", domain or "default")
        .strip("_")
        .lower()
        or "default"
    )
    candidates: list[str] = []
    if uc_schema:
        candidates.append(
            format_mlflow_template(
                PROMPT_NAME_TEMPLATE,
                uc_schema=uc_schema,
                judge_name=judge_name,
            )
        )
        candidates.append(
            f"{uc_schema}.genie_opt_{safe_domain}_{judge_name}"
        )
    candidates.append(f"genie_opt_{safe_domain}_{judge_name}")
    return list(dict.fromkeys(candidates))
```

### Candidate Priority Order

Given `uc_schema="main.genie_optimization"`, `domain="sales_analytics"`,
`judge_name="syntax_validity"`:

| Priority | Candidate | Notes |
|----------|-----------|-------|
| 1 | `main.genie_optimization.genie_opt_syntax_validity` | From `PROMPT_NAME_TEMPLATE`, standard name |
| 2 | `main.genie_optimization.genie_opt_sales_analytics_syntax_validity` | Domain-scoped, avoids collisions |
| 3 | `genie_opt_sales_analytics_syntax_validity` | Portable — no UC prefix, works without schema |

The `dict.fromkeys()` call deduplicates if the template and domain-scoped
names happen to produce the same string.

---

## Retry Logic with Ordered Candidate List

The registration loop in `register_judge_prompts()` (lines 2241–2309)
implements this retry strategy:

```
FOR each judge_name in JUDGE_PROMPTS:
    candidates = _prompt_name_candidates(uc_schema, domain, judge_name)
    FOR each prompt_name in candidates:
        TRY register_prompt(name=prompt_name, ...)
            set_prompt_alias(name=prompt_name, ...)
            → SUCCESS: break inner loop
        EXCEPT:
            IF _is_ownership_conflict(error):
                TRY _try_drop_prompt(prompt_name)
                    register_prompt(name=prompt_name, ...)  # retry after drop
                    set_prompt_alias(...)
                    → SUCCESS: break inner loop
            classify error → log warning with remediation
            continue to next candidate
    IF no candidate succeeded:
        mark judge as failed, record all attempt details
```

### State Tracking

Successful registrations are stored in the module-level
`_REGISTERED_PROMPT_NAMES` dict so downstream code (e.g., `_link_prompt_to_trace`)
knows which name was actually registered:

```python
_REGISTERED_PROMPT_NAMES: dict[str, str] = {}

# After successful registration:
_REGISTERED_PROMPT_NAMES[judge_name] = prompt_name
```

---

## Full Implementation with Logging and Metrics

Putting it all together — a self-contained registration function with
classification, retry, and metrics:

```python
import logging
import re
from typing import Any

import mlflow
import mlflow.genai

logger = logging.getLogger(__name__)

PROMPT_REGISTRY_REQUIRED_PRIVILEGES = ("CREATE FUNCTION", "EXECUTE", "MANAGE")
_REGISTERED_NAMES: dict[str, str] = {}


def register_prompt_resilient(
    uc_schema: str,
    domain: str,
    judge_name: str,
    template: str,
    alias: str = "production",
) -> dict[str, Any] | None:
    """Register a prompt with fallback candidates and ownership recovery.

    Returns registration info dict on success, None on total failure.
    """
    candidates = _prompt_name_candidates(uc_schema, domain, judge_name)
    attempt_failures: list[dict[str, Any]] = []

    for prompt_name in candidates:
        try:
            version = mlflow.genai.register_prompt(
                name=prompt_name,
                template=template,
                commit_message=f"Judge: {judge_name} (domain: {domain})",
                tags={"domain": domain, "type": "judge"},
            )
            mlflow.genai.set_prompt_alias(
                name=prompt_name,
                alias=alias,
                version=version.version,
            )
            _REGISTERED_NAMES[judge_name] = prompt_name
            logger.info(
                "Registered %s v%s with alias @%s",
                prompt_name, version.version, alias,
            )
            return {
                "prompt_name": prompt_name,
                "version": version.version,
                "alias": alias,
            }
        except Exception as exc:
            err_msg = str(exc).strip()

            if _is_ownership_conflict(err_msg) and _try_drop_prompt(prompt_name):
                try:
                    version = mlflow.genai.register_prompt(
                        name=prompt_name,
                        template=template,
                        commit_message=f"Judge: {judge_name} (re-created)",
                        tags={"domain": domain, "type": "judge"},
                    )
                    mlflow.genai.set_prompt_alias(
                        name=prompt_name,
                        alias=alias,
                        version=version.version,
                    )
                    _REGISTERED_NAMES[judge_name] = prompt_name
                    logger.info(
                        "Registered %s v%s (re-created after drop)",
                        prompt_name, version.version,
                    )
                    return {
                        "prompt_name": prompt_name,
                        "version": version.version,
                        "alias": alias,
                    }
                except Exception:
                    pass

            classification = _classify_prompt_registration_error(
                err_msg, uc_schema=uc_schema,
            )
            attempt_failures.append({
                "prompt_name": prompt_name,
                "error": err_msg[:1500],
                "classification": classification["reason"],
                "remediation": classification["remediation"],
            })
            logger.warning(
                "Registration failed for %s name=%s cause=%s",
                judge_name, prompt_name, classification["reason"],
            )

    logger.error(
        "All candidates exhausted for %s. Failures: %s",
        judge_name, attempt_failures,
    )
    return None
```

---

## Prevention: Avoiding Ownership Conflicts

| Strategy | How |
|----------|-----|
| **Single SP per schema** | All jobs and apps that register prompts in a schema use the same service principal. |
| **MANAGE privilege** | Grant `MANAGE` on the schema to all registering principals (allows updating others' functions). |
| **Schema ownership** | Transfer schema ownership to a shared group that includes all SPs. |
| **Separate schemas per team** | Each team gets its own schema, avoiding cross-ownership entirely. |
| **Deploy script grants** | The `deploy.sh` script grants UC privileges as part of setup. |

---

## Source References

- `evaluation.py` line 1976: `_is_ownership_conflict()`
- `evaluation.py` lines 1982–1999: `_try_drop_prompt()`
- `evaluation.py` lines 2002–2057: `_classify_prompt_registration_error()`
- `evaluation.py` lines 2549–2557: `_prompt_name_candidates()`
- `evaluation.py` lines 2241–2309: registration loop with retry
- `config.py` line 1973: `PROMPT_REGISTRY_REQUIRED_PRIVILEGES`

## Related References

- [uc-schema-linkage.md](uc-schema-linkage.md) — schema setup and permissions.
- [loading-patterns.md](loading-patterns.md) — loading prompts after registration.
- [ab-testing.md](ab-testing.md) — alias management patterns.

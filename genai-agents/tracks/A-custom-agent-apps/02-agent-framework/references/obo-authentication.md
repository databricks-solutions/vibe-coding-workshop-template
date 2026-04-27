# On-Behalf-Of (OBO) Authentication

OBO enables agents to query data on behalf of the calling user, respecting per-user permissions.

**CRITICAL:** OBO **only works in Model Serving**. Attempting OBO in notebooks/jobs/evaluation produces invalid credentials and permission errors.

---

## Context Detection Pattern (MANDATORY)

**Always detect execution context before attempting OBO:**

```python
def _get_authenticated_client(self):
    """
    Get WorkspaceClient with appropriate auth strategy.
    
    CRITICAL: OBO only works in Model Serving context.
    Outside Model Serving, use default auth (user credentials or service principal).
    
    Production Learning: Jan 27, 2026
    Problem: Agent evaluation failed with "You need 'Can View' permission" errors
    Root Cause: OBO attempted outside Model Serving -> invalid credentials
    Solution: Detect environment before attempting OBO
    """
    from databricks.sdk import WorkspaceClient
    import os
    
    # ================================================================
    # STEP 1: Detect if we're running in Model Serving environment
    # ================================================================
    # Model Serving sets specific environment variables:
    # - IS_IN_DB_MODEL_SERVING_ENV=true (Databricks Model Serving)
    # - DATABRICKS_SERVING_ENDPOINT (endpoint name)
    # - MLFLOW_DEPLOYMENT_FLAVOR_NAME=databricks (MLflow deployment)
    # ================================================================
    is_model_serving = (
        os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true" or
        os.environ.get("DATABRICKS_SERVING_ENDPOINT") is not None or
        os.environ.get("MLFLOW_DEPLOYMENT_FLAVOR_NAME") == "databricks"
    )
    
    # ================================================================
    # STEP 2: Use OBO only in Model Serving, default auth otherwise
    # ================================================================
    if is_model_serving:
        # We're in Model Serving - attempt OBO authentication
        try:
            from databricks_ai_bridge import ModelServingUserCredentials
            client = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
            print(f"Using on-behalf-of-user auth (Model Serving)")
            return client
        except ImportError:
            # databricks-ai-bridge not installed
            print(f"databricks-ai-bridge not available, falling back to default auth")
            return WorkspaceClient()
        except Exception as auth_e:
            # OBO setup failed
            print(f"OBO auth failed: {type(auth_e).__name__}: {auth_e}")
            print(f"Falling back to default auth")
            return WorkspaceClient()
    else:
        # Not in Model Serving - use default auth (notebooks, jobs, evaluation)
        # This uses the current user's credentials or service principal
        print(f"Using default workspace auth (evaluation/notebook mode)")
        return WorkspaceClient()
```

## Environment Variables Reference

| Variable | Set When | Value |
|---|---|---|
| `IS_IN_DB_MODEL_SERVING_ENV` | Model Serving | `"true"` |
| `DATABRICKS_SERVING_ENDPOINT` | Model Serving | Endpoint name |
| `MLFLOW_DEPLOYMENT_FLAVOR_NAME` | MLflow deployment | `"databricks"` |

## Why Context Detection Is Critical

| Environment | OBO Attempted | Result |
|---|---|---|
| **Notebooks** without detection | Yes | Permission errors (invalid credentials) |
| **Notebooks** with detection | No (uses default) | Works (uses your credentials) |
| **Jobs** without detection | Yes | Permission errors (invalid credentials) |
| **Jobs** with detection | No (uses default) | Works (uses job owner/SP credentials) |
| **Evaluation** without detection | Yes | Permission errors (invalid credentials) |
| **Evaluation** with detection | No (uses default) | Works (uses runner credentials) |
| **Model Serving** with OBO | Yes | Works (uses end-user credentials) |

---

## Model Serving Configuration

**Enable OBO in serving endpoint YAML:**

```yaml
# File: resources/agents/agent_serving_endpoint.yml

resources:
  model_serving_endpoints:
    health_monitor_agent:
      name: health-monitor-agent
      config:
        served_entities:
          - name: current
            entity_name: ${var.catalog}.${var.agent_schema}.health_monitor_agent
            entity_version: "${var.agent_version}"
            workload_size: Small
            scale_to_zero_enabled: true
            
            # ================================================================
            # CRITICAL: Enable on-behalf-of authentication
            # This allows the agent to access data as the calling user.
            # ================================================================
            environment_vars:
              # Enable OBO for Genie and SDK
              DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"
              
              # Pass Genie Space IDs
              COST_GENIE_SPACE_ID: ${var.cost_genie_space_id}
              SECURITY_GENIE_SPACE_ID: ${var.security_genie_space_id}
              PERFORMANCE_GENIE_SPACE_ID: ${var.performance_genie_space_id}
              RELIABILITY_GENIE_SPACE_ID: ${var.reliability_genie_space_id}
              QUALITY_GENIE_SPACE_ID: ${var.quality_genie_space_id}
              UNIFIED_GENIE_SPACE_ID: ${var.unified_genie_space_id}
        
        # Traffic configuration
        traffic_config:
          routes:
            - served_model_name: current
              traffic_percentage: 100
```

---

## Automatic Authentication Passthrough (CRITICAL)

**CRITICAL:** OBO context detection alone is NOT sufficient. Even with default `WorkspaceClient()`, evaluation will FAIL if Genie Spaces are not declared as resources!

**Problem (Jan 27, 2026):** After implementing OBO context detection, evaluation still failed with:
```
You need "Can View" permission to perform this action. Config: host=..., auth_type=runtime
```

**Root Cause:** MLflow agents have TWO separate authentication mechanisms:

| Mechanism | Context | How It Works |
|---|---|---|
| **OBO (On-Behalf-Of-User)** | Model Serving | Uses end-user credentials via `UserAuthPolicy` scopes |
| **Automatic Auth Passthrough** | Evaluation/Notebooks | Databricks creates SERVICE PRINCIPAL with access to declared `resources` |

Without declaring `DatabricksGenieSpace` resources, the service principal has NO Genie access!

**Official Documentation Quote:**
> "Remember to log all downstream dependent resources, too. For example, if you log a Genie Space, you must also log its tables, SQL Warehouses, and Unity Catalog functions."

### Resource Declaration Pattern

```python
from mlflow.models.auth_policy import AuthPolicy, SystemAuthPolicy, UserAuthPolicy
from mlflow.models.resources import (
    DatabricksGenieSpace,
    DatabricksSQLWarehouse,
    DatabricksServingEndpoint,
    DatabricksLakebase,
)

def get_mlflow_resources():
    """
    Get ALL resources for Automatic Authentication Passthrough.
    
    CRITICAL: Include Genie Spaces AND SQL Warehouse!
    Without these, evaluation/notebook contexts cannot access Genie.
    
    Minimum MLflow versions:
    - DatabricksGenieSpace: 2.17.1+
    - DatabricksSQLWarehouse: 2.16.1+
    """
    resources = []
    
    # LLM endpoint
    resources.append(DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT))
    
    # Memory storage (if using Lakebase)
    resources.append(DatabricksLakebase(database_instance_name=LAKEBASE_INSTANCE))
    
    # ================================================================
    # CRITICAL: Add ALL Genie Spaces
    # ================================================================
    # Service principal needs "Can Run" on each Genie Space
    # ================================================================
    for domain, space_id in GENIE_SPACES.items():
        if space_id:
            resources.append(DatabricksGenieSpace(genie_space_id=space_id))
            print(f"Added DatabricksGenieSpace: {domain} ({space_id})")
    
    # ================================================================
    # CRITICAL: Add SQL Warehouse for Genie query execution
    # ================================================================
    # Service principal needs "CAN USE" on the warehouse
    # ================================================================
    resources.append(DatabricksSQLWarehouse(warehouse_id=WAREHOUSE_ID))
    print(f"Added DatabricksSQLWarehouse: {WAREHOUSE_ID}")
    
    return resources


def get_auth_policy():
    """
    Get combined AuthPolicy with BOTH system and user authentication.
    
    BOTH are required for complete coverage:
    - SystemAuthPolicy: For evaluation/notebook contexts (service principal)
    - UserAuthPolicy: For Model Serving contexts (end-user credentials via OBO)
    """
    # ================================================================
    # System policy: ALL resources for automatic auth passthrough
    # ================================================================
    # This creates a service principal with access to these resources.
    # Used in evaluation/notebook contexts where OBO doesn't work.
    # ================================================================
    system_resources = get_mlflow_resources()
    system_policy = SystemAuthPolicy(resources=system_resources)
    
    # ================================================================
    # User policy: API scopes for OBO in Model Serving
    # ================================================================
    # These scopes allow the agent to use end-user credentials
    # for Genie queries in production.
    # ================================================================
    user_policy = UserAuthPolicy(api_scopes=[
        "dashboards.genie",           # Genie Space access
        "sql.warehouses",             # SQL Warehouse access
        "sql.statement-execution",    # Execute SQL statements
        "serving.serving-endpoints",  # LLM endpoint calls
    ])
    
    return AuthPolicy(
        system_auth_policy=system_policy,
        user_auth_policy=user_policy
    )


# Log model with auth_policy (NOT just resources!)
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model=agent,
    auth_policy=get_auth_policy(),  # Includes BOTH system and user policies
    pip_requirements=[
        "mlflow>=3.0.0",
        "databricks-sdk>=0.30.0",
        "databricks-ai-bridge>=0.1.0",  # OBO support
    ],
)
```

### Authentication Flow

```
+------------------------------------------------------------------+
|                    Agent Authentication Flow                       |
+------------------------------------------------------------------+
|                                                                    |
|  Model Logging (mlflow.pyfunc.log_model)                           |
|  +-- auth_policy.system_auth_policy.resources                      |
|  |   +-- Creates SERVICE PRINCIPAL with access to resources        |
|  +-- auth_policy.user_auth_policy.api_scopes                      |
|      +-- Declares API scopes for OBO                               |
|                                                                    |
|  Runtime Context Detection (_get_authenticated_client)             |
|  +-- Model Serving Environment?                                    |
|  |   +-- YES -> Use OBO (end-user credentials via scopes)          |
|  |   +-- NO  -> Use default auth (service principal via resources) |
|  +-- Result: Correct auth for BOTH contexts                        |
|                                                                    |
+------------------------------------------------------------------+
```

### Required Resources Table

| Resource Type | Class | Permission Needed | Min MLflow |
|---|---|---|---|
| Genie Space | `DatabricksGenieSpace` | Can Run | 2.17.1 |
| SQL Warehouse | `DatabricksSQLWarehouse` | CAN USE | 2.16.1 |
| LLM Endpoint | `DatabricksServingEndpoint` | Can Query | 2.13.1 |
| Lakebase | `DatabricksLakebase` | databricks_superuser | 3.3.2 |

---

## Common OBO Errors and Fixes

### Error 1: Permission Denied Outside Model Serving

**Symptom:**
```
Genie query failed: You need "Can View" permission to perform this action.
Config: host=https://..., auth_type=runtime
```

**Root Cause:** OBO attempted in notebook/job/evaluation (invalid credentials)

**Fix:** Add context detection (see pattern above)

### Error 2: databricks-ai-bridge Import Error

**Symptom:**
```
ImportError: No module named 'databricks_ai_bridge'
```

**Root Cause:** Package not installed

**Fix:** Install package (graceful fallback already handled in pattern):
```bash
%pip install databricks-ai-bridge
dbutils.library.restartPython()
```

### Error 3: OBO Works in Serving but Fails in Eval

**Symptom:**
```
# Model Serving: Works
# Evaluation: Permission errors
```

**Root Cause:** Evaluation doesn't have Model Serving environment variables

**Expected Behavior:** This is correct! Evaluation uses your credentials, not OBO.

**Validation:**
```python
import os

# In evaluation/notebook - should be False
is_model_serving = os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true"
print(f"Model Serving: {is_model_serving}")  # False

# In Model Serving - should be True
is_model_serving = os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true"
print(f"Model Serving: {is_model_serving}")  # True
```

---

## OBO Dependencies

**Required Package:**
```
databricks-ai-bridge>=0.1.0  # For ModelServingUserCredentials
```

**Add to model logging:**
```python
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model=agent,
    pip_requirements=[
        "mlflow>=3.0.0",
        "databricks-sdk>=0.30.0",
        "databricks-ai-bridge>=0.1.0",  # OBO support
    ],
    ...
)
```

---

## Validation Checklist

### Resource Declaration (for Evaluation/Notebooks)

- [ ] ALL Genie Spaces declared via `DatabricksGenieSpace(genie_space_id=...)`
- [ ] SQL Warehouse declared via `DatabricksSQLWarehouse(warehouse_id=...)`
- [ ] LLM endpoint declared via `DatabricksServingEndpoint(endpoint_name=...)`
- [ ] Lakebase (if used) declared via `DatabricksLakebase(database_instance_name=...)`
- [ ] Resources included in `SystemAuthPolicy(resources=[...])`
- [ ] `auth_policy` parameter passed to `mlflow.pyfunc.log_model()`

### OBO Configuration (for Model Serving)

- [ ] Context detection implemented in auth client initialization
- [ ] Environment variable checks include all three variables
- [ ] Graceful fallback to default auth if OBO fails
- [ ] Logging shows which auth mode is active
- [ ] `databricks-ai-bridge` in pip_requirements
- [ ] API scopes declared in `UserAuthPolicy(api_scopes=[...])`
- [ ] Serving endpoint has `DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"`

### Testing

- [ ] Tested in notebook (should use default auth via service principal)
- [ ] Tested in Model Serving (should use OBO with end-user credentials)
- [ ] Genie queries succeed in evaluation context
- [ ] Genie queries succeed in Model Serving context
- [ ] User audit logging includes user_id in Model Serving
- [ ] Error messages don't expose credentials

---

## Production Learnings

### Jan 27, 2026 - Part 1: OBO Context Detection Fix

**Problem:** Agent evaluation failing with permission errors despite user having proper permissions

**Root Cause:** Code attempted OBO if `databricks-ai-bridge` was installed, regardless of execution context. OBO produces invalid credentials outside Model Serving.

**Solution:** Added environment variable checks to detect Model Serving context:
- Check `IS_IN_DB_MODEL_SERVING_ENV == "true"`
- Check `DATABRICKS_SERVING_ENDPOINT is not None`
- Check `MLFLOW_DEPLOYMENT_FLAVOR_NAME == "databricks"`

### Jan 27, 2026 - Part 2: Genie Resource Declaration Fix

**Problem:** After implementing OBO context detection, evaluation STILL failed with:
```
You need "Can View" permission to perform this action. Config: host=..., auth_type=runtime
```

**Root Cause:** MLflow agents have TWO authentication mechanisms:
1. **OBO** - for Model Serving (uses `UserAuthPolicy` scopes)
2. **Automatic Auth Passthrough** - for evaluation/notebooks (uses `SystemAuthPolicy` resources)

The code had OBO configured via `user_auth_policy`, but `system_auth_policy.resources` did NOT include Genie Spaces! Without declaring `DatabricksGenieSpace` resources, the service principal created by Databricks has NO Genie access.

**Solution (3 parts):**
1. Add `DatabricksGenieSpace(genie_space_id=...)` for ALL Genie Spaces
2. Add `DatabricksSQLWarehouse(warehouse_id=...)` for query execution
3. Include ALL resources in `SystemAuthPolicy.resources`

**Impact:**
- Evaluation now works with service principal credentials
- Model Serving continues to work with OBO
- Same code works across all environments
- No runtime permission errors in any context

**Key Learning:** MLflow agent authentication has TWO SEPARATE mechanisms that work in different contexts:
- `user_auth_policy` -> OBO in Model Serving
- `system_auth_policy` -> Automatic passthrough in evaluation/notebooks

**BOTH must be configured.** Missing either one causes 100% failures in that context.

**Reference:** [Official Databricks Agent Authentication Docs](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication)

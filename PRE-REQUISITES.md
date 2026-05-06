# Workshop prerequisites (monorepo)

> **Scope:** This repo supports **Apps Lakebase** (Databricks AppKit + Lakebase workshop) and **Data Product Accelerator** (medallion / Genie SDK prompts). The same workspace checklist applies at a high level; **not every row applies to every delivery** — use the **scope tags** below and the **Overview** “Applies to” column.

> **Purpose:** Everything participants and admins need in place **before** the workshop so the session focuses on building, not firefighting setup.

> **How the workshop runs:** Deliveries use **Genie Code** — Databricks notebooks on **serverless** compute. No local IDE or local toolchain is required for the paths described in this document.

### Scope legend (tags used in this document)

| Tag | Meaning |
|-----|--------|
| **Common** | Baseline workspace / UC / compute / SQL warehouse — relevant to most deliveries |
| **Genie** | Databricks notebooks / serverless |
| **AppKit-MCP** | Apps Lakebase with MCP — requires **`mcp-appkit-skill`** + **`v2v-gc-agent`** (see **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md)**) |
| **DPA** | Data Product Accelerator — shared catalog `donotdelete_vibe_coding_catalog` and medallion prompts |

---

## Overview

| # | Prerequisite | Owner | Estimated Time | Applies to |
|---|---|---|---|---|
| 1 | Workspace access for participants | Admin | 1–2 days (AD group provisioning) | Common · Genie |
| 2 | Unity Catalog access (+ [§2b](#2b-data-product-accelerator-catalog-dpa-track-only) DPA catalog when needed) | Admin | 30 min | Common · **DPA** · Genie |
| 3 | Serverless SQL Warehouse access | Admin | 15 min | Common · Genie |
| 4 | Serverless General Compute access (budget policy) | Admin | 15 min | Common · Genie |
| 5 | Databricks Apps enabled with Lakebase access | Admin | 30 min | Common · Genie (Apps Lakebase path; DPA still needs compute) |
| 6 | MCP AppKit Skill app + SP + secret scope | Admin | ~45 min | **AppKit-MCP** · Genie — see **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md)** |

> **Facilitator:** Ordered admin + day-of steps: **[`WORKSHOP-FACILITATOR-GUIDE.md`](WORKSHOP-FACILITATOR-GUIDE.md) §0 — End-to-end facilitator checklist**.

---

## Admin prerequisites (complete before the workshop)

These steps are typically performed by a **Workspace Admin** or **Account Admin** in advance.

### 1. Workspace access for participants

**Scope:** Common · Genie

Participants must be able to log in to the Databricks workspace used for the workshop.

- **Recommended approach:** Create a dedicated **AD (Active Directory) group** (e.g., `workshop-participants`) and assign all attendees to it.
- Grant the AD group access to the target Databricks workspace.
- Verify that each participant can successfully log in to the workspace URL.

> **Tip:** Send participants the workspace URL and ask them to confirm login access at least **48 hours** before the workshop.

---

### 2. Unity Catalog access — catalog + schema creation privileges

**Scope:** Common · Genie (see [§2b](#2b-data-product-accelerator-catalog-dpa-track-only) for **DPA** catalog)

Each participant (or team) needs the ability to create and manage their own schema within a designated catalog.

- **Create a workshop catalog** (e.g., `workshop` or `workshop_<date>`) or designate an existing one.
- Grant the AD group the following privileges:

```sql
-- Grant catalog-level usage
GRANT USE CATALOG ON CATALOG workshop TO `workshop-participants`;

-- Grant the ability to create schemas within the catalog
GRANT CREATE SCHEMA ON CATALOG workshop TO `workshop-participants`;
```

- Each participant will create their own schema during the workshop (e.g., `workshop.john_doe`).

> **Why:** The workshop involves creating Bronze, Silver, and Gold layer tables, metric views, and other assets. Participants need their own isolated schema to avoid conflicts.

---

### 2b. Data Product Accelerator catalog (DPA track only)

**Scope:** **DPA** · Genie — required for DPA medallion workshop; skip if you only run Apps Lakebase

The Data Product Accelerator workshop hardcodes the catalog name `donotdelete_vibe_coding_catalog` in all prompts. Each participant creates their own per-user Bronze, Silver, and Gold schemas inside this shared catalog. **This catalog must exist before the workshop starts.**

#### Create the catalog (notebook — admin)

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.catalogs.create(name="donotdelete_vibe_coding_catalog")
print("✓ Catalog created")
```

#### Grant permissions to all participants

```sql
-- Allow participants to browse the catalog
GRANT USE CATALOG ON CATALOG donotdelete_vibe_coding_catalog TO `users`;

-- Allow participants to create their own schemas
GRANT CREATE SCHEMA ON CATALOG donotdelete_vibe_coding_catalog TO `users`;
```

**Or via SDK:**

```python
from databricks.sdk.service.catalog import SecurableType, PermissionsChange, Privilege

w.grants.update(
    securable_type=SecurableType.CATALOG,
    full_name="donotdelete_vibe_coding_catalog",
    changes=[
        PermissionsChange(
            add=[Privilege.USE_CATALOG, Privilege.CREATE_SCHEMA],
            principal="account users",
        ),
    ],
)
print("✓ Permissions granted")
```

> **Important:** Do NOT delete this catalog during or after the workshop — it is shared across all attendees and contains their per-user schemas (e.g., `jaiwant_j_booking_app_bronze`, `jaiwant_j_booking_app_silver`, `jaiwant_j_booking_app_gold`). Schema names are user-specific so they will not conflict between participants.

#### Verify

```python
from databricks.sdk.service.catalog import SecurableType

catalog = w.catalogs.get("donotdelete_vibe_coding_catalog")
print(f"✓ Catalog exists: {catalog.name} (owner: {catalog.owner})")

grants = w.grants.get(
    securable_type=SecurableType.CATALOG,
    full_name="donotdelete_vibe_coding_catalog",
)
for g in grants.privilege_assignments or []:
    print(f"  {g.principal}: {[p.value for p in g.privileges]}")
```

---

### 3. Serverless SQL Warehouse access

**Scope:** Common · Genie

Participants need access to a **Serverless SQL Warehouse** for running queries, creating metric views, TVFs, and Genie Spaces.

- Create a shared Serverless SQL Warehouse (e.g., `Workshop SQL Warehouse`) or use an existing one.
- Grant the AD group `CAN USE` permission on the warehouse.
- Ensure the warehouse is set to **Serverless** (not Classic or Pro).

> **Sizing guidance:** A `Small` Serverless SQL Warehouse is typically sufficient for workshop-sized workloads.

---

### 4. Serverless General Compute access (budget policy)

**Scope:** Common · Genie

Participants need access to **Serverless General Compute** for running notebooks and jobs.

- Enable Serverless compute for the workspace (if not already enabled).
- **Create a budget policy** for workshop participants to control cost:
  - Navigate to **Compute > Budget Policies** in the workspace.
  - Create a policy (e.g., `workshop-budget-policy`) with appropriate limits.
  - Assign the policy to the `workshop-participants` AD group.
- Grant the AD group permission to create and use Serverless compute.

> **Important:** Without a budget policy, participants may not be able to launch Serverless compute. Verify this is configured before the workshop.

---

### 5. Databricks Apps enabled with Lakebase access

**Scope:** Common · Genie — **Apps Lakebase** requires Apps + Lakebase; **DPA Genie** still needs Serverless compute ([§4](#4-serverless-general-compute-access-budget-policy)) even if participants do not deploy an App

The workshop builds **Databricks Apps** backed by **Lakebase** (managed PostgreSQL). Both features must be enabled for the Apps Lakebase track.

#### 5a. Enable Databricks Apps

- Navigate to **Workspace Settings > Compute > Databricks Apps**.
- Ensure Apps are **enabled** for the workspace.
- Grant the AD group the **Consumer** entitlement so participants can access deployed Apps:
  - Navigate to **Workspace Settings > Identity and access > Groups**.
  - Select the `workshop-participants` group.
  - Under **Entitlements**, enable **Consumer**.

> **Note:** Databricks Apps run on dedicated Serverless compute. No additional cluster configuration is required.

#### 5b. Enable Lakebase (Managed PostgreSQL)

- Ensure Lakebase is **enabled** for the workspace:
  - Navigate to **Workspace Settings > Compute > Lakebase**.
  - Enable the feature if not already active.
- Grant the AD group permission to create and access Lakebase databases (align with your UC model; example):

```sql
GRANT USE CATALOG ON CATALOG workshop TO `workshop-participants`;
GRANT CREATE SCHEMA ON CATALOG workshop TO `workshop-participants`;
```

> **Sizing guidance:** Lakebase instances for workshop use are lightweight — the default configuration is sufficient for up to 50 concurrent participants.

---

### 6. MCP AppKit (Apps Lakebase with MCP only)

**Scope:** **AppKit-MCP** · Genie — **skip** for DPA-only Genie without AppKit MCP

For **Apps Lakebase Genie** workshops that use **MCP AppKit** tools, admins must deploy **`mcp-appkit-skill`** and configure the shared **`v2v-gc-agent`** secret scope **before** participants open **[`apps_lakebase/prompts/mcp-setup-gc.md`](apps_lakebase/prompts/mcp-setup-gc.md)**.

**Full procedure (deploy app, service principal, OAuth secret, ACLs, verification):** **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md)**

---

## Participant prerequisites (Genie Code)

These steps apply in the **Databricks workspace** (notebooks / Genie Code). There is no separate local setup checklist in this document.

### Apps Lakebase Genie (with MCP)

- Confirm login to the workshop workspace.
- At session start, run **[`apps_lakebase/prompts/mcp-setup-gc.md`](apps_lakebase/prompts/mcp-setup-gc.md)** Step 1 after admins complete **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md)**.
- Then follow **[`apps_lakebase/prompts/README.md`](apps_lakebase/prompts/README.md)** (Genie order); optional context: [`apps_lakebase/Instructions.md`](apps_lakebase/Instructions.md).

### Data Product Accelerator Genie

- Confirm login to the workshop workspace.
- No MCP is required for the core medallion flow — start from **[`data_product_accelerator/gc-prompt-conversion/workshop-variables.md`](data_product_accelerator/gc-prompt-conversion/workshop-variables.md)** and **[`data_product_accelerator/QUICKSTART.md`](data_product_accelerator/QUICKSTART.md)** / **`data_product_accelerator/prompts/*-gc.md`** in stage order.

---

## Pre-workshop checklist

### Admin checklist — common foundation (all deliveries)

- [ ] AD group created and all participants added
- [ ] Participants can log in to the workspace
- [ ] Workshop catalog created with `CREATE SCHEMA` privileges granted
- [ ] `donotdelete_vibe_coding_catalog` created with `USE CATALOG` + `CREATE SCHEMA` granted to `users` (**DPA** — [§2b](#2b-data-product-accelerator-catalog-dpa-track-only))
- [ ] Serverless SQL Warehouse provisioned and accessible
- [ ] Serverless General Compute enabled with budget policy assigned
- [ ] Databricks Apps enabled in workspace settings
- [ ] Lakebase enabled in workspace settings
- [ ] AD group granted Consumer entitlement

### Admin checklist — AppKit-MCP (Apps Lakebase Genie with MCP only)

Skip for **DPA-only Genie** without AppKit MCP. Use **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md) §6 checklist**.

### Participant checklist — Genie Code

- [ ] Can log in to the Databricks workspace
- [ ] **Apps Lakebase + MCP:** MCP connectivity verified at workshop start — [`apps_lakebase/prompts/mcp-setup-gc.md`](apps_lakebase/prompts/mcp-setup-gc.md) Step 1 (after admin **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md)**)
- [ ] **DPA Genie:** Workshop repo accessible; run `workshop-variables.md` bootstrap then follow `data_product_accelerator/QUICKSTART.md` / `prompts/*-gc.md` order

---

## Troubleshooting common issues

| Issue | Resolution |
|---|---|
| **Cannot log in to workspace** | Confirm AD group membership with your admin. Allow up to 24 hours for provisioning. |
| **"Permission denied" on catalog** | Admin needs to run the `GRANT` statements from [§2](#2-unity-catalog-access--catalog--schema-creation-privileges). |
| **Schema creation fails in DPA workshop** | Admin: run `GRANT USE CATALOG` + `GRANT CREATE SCHEMA ON CATALOG donotdelete_vibe_coding_catalog TO users` from [§2b](#2b-data-product-accelerator-catalog-dpa-track-only). |
| **`donotdelete_vibe_coding_catalog` not found** | Admin: create the catalog with the SDK snippet in [§2b](#2b-data-product-accelerator-catalog-dpa-track-only). |
| **Serverless compute not available** | Admin needs to enable Serverless compute and assign a budget policy ([§4](#4-serverless-general-compute-access-budget-policy)). |
| **Databricks Apps not available** | Admin needs to enable Apps in Workspace Settings > Compute > Databricks Apps ([§5](#5-databricks-apps-enabled-with-lakebase-access)). |
| **Lakebase not available** | Admin needs to enable Lakebase in Workspace Settings > Compute > Lakebase ([§5](#5-databricks-apps-enabled-with-lakebase-access)). |
| **MCP `401` / `403` / secrets / app not ACTIVE** | See **[`pre-req-mcp-setup.md`](pre-req-mcp-setup.md) §5 Troubleshooting**. |

---

## Need help?

If you run into issues completing these prerequisites, please reach out to the workshop organizers **before** the session so we can troubleshoot together. We want everyone ready to build on day one.

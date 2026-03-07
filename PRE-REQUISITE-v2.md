# Vibe Coding Workshop — Prerequisites Guide

> **Purpose:** Everything that must be in place **before** the workshop begins. Completing these steps ahead of time ensures participants can focus on building, not troubleshooting setup issues.
>
> **How the workshop runs:** The workshop is delivered as a **Databricks App** backed by **Lakebase** (managed PostgreSQL). A guided web interface walks participants through multi-chapter workflows — from app UI design through Lakehouse pipelines to GenAI agent deployment. Participants use an AI-powered IDE alongside the App to build production-grade Databricks solutions.

---

## How to Use This Document

| Chapter | Audience | What It Covers |
|---------|----------|----------------|
| [1. Workspace Setup](#chapter-1-workspace-setup) | Account Admin | Create or designate the workshop workspace |
| [2. Data Infrastructure](#chapter-2-data-infrastructure) | Workspace Admin | Lakebase instance, SQL Warehouse, Unity Catalog & permissions |
| [3. Model Serving & App Deployment](#chapter-3-model-serving--app-deployment) | Workspace Admin | LLM endpoint access, deploy the workshop app |
| [4. Authentication](#chapter-4-authentication) | Admin + Participants | OAuth (preferred), PAT (alternative), CLI setup |
| [5. Admin Cleanup (Post-Workshop)](#chapter-5-admin-cleanup-post-workshop) | Admin | Tear down resources after the workshop |

---

# Chapter 1: Workspace Setup

**Owner:** Account Admin 

### 1.1 Create or Designate the Workshop Workspace (30 minutes)

You need a Databricks workspace where all participants will work. Choose one of the following approaches:

| Approach | When to Use |
|----------|-------------|
| **Create a new workspace** | Recommended for clean isolation and easy post-workshop cleanup (delete the entire workspace) |
| **Use an existing workspace** | When a shared dev/sandbox workspace is already available |

#### Option A — Create a New Workspace (Recommended)

1. Log in to the **Databricks Account Console** at `https://accounts.cloud.databricks.com`.
2. Navigate to **Workspaces** > **Create Workspace**.
3. Configure:
   - **Name:** e.g., `vibe-coding-workshop` (or `vibe-coding-workshop-<customer>`)
   - **Region:** Choose the region closest to participants
   - **Pricing Tier:** Premium or Enterprise (required for Unity Catalog and Serverless)
4. Wait for the workspace to reach **Running** state (typically 5–10 minutes).
5. Note the **Workspace URL** — this becomes the **Databricks Workspace URL** parameter in the app.
6. Note the **Workspace Org ID** from the URL query parameter `?o=` — this becomes the **Workspace Org ID** parameter in the app.

#### Option B — Use an Existing Workspace

1. Confirm the workspace has **Premium** or **Enterprise** tier (required for Unity Catalog and Serverless compute).
2. Record the **Workspace URL** and **Org ID**.

### 1.2 Add Participants to the Workspace (Up to 2 days)

- **Recommended:** Create a dedicated **AD/SCIM group** (e.g., `workshop-participants`) and add all attendees.
- Grant the group access to the target workspace via the Account Console.
- Verify each participant can log in.

> **Tip:** Send participants the workspace URL and ask them to confirm login access at least **48 hours** before the workshop.

**Parameters to record:**

| Parameter | Value |
|---|---|
| **Databricks Workspace URL** | `https://your-workspace.cloud.databricks.com` |
| **Workspace Org ID** | The numeric ID from the `?o=` URL parameter |

---

# Chapter 2: Data Infrastructure

**Owner:** Workspace Admin  
**Estimated Time:** 45 min

This chapter creates three core resources that power the workshop: a **Lakebase instance** (app backend database), a **Serverless SQL Warehouse** (query engine), and a **Unity Catalog catalog** (Lakehouse storage). Permissions are configured so all workspace users can create schemas and tables.

### 2.1 Create a Lakebase Instance (Provisioned)

Lakebase is managed PostgreSQL on Databricks. The workshop app uses it to store session state, prompts, and progress.

#### Via the UI

1. Navigate to **Catalog** > **Lakebase** (or **Compute** > **Lakebase**, depending on workspace version).
2. Click **Create Instance**.
3. Configure:
   - **Name:** `vibe-coding-workshop-lakebase` (or your preferred naming convention)
   - **Capacity Mode:** **Provisioned** (select `CU_1` for workshops up to 50 participants)
4. Wait for the instance to reach **RUNNING** state.
5. Record the **Instance Name** and **Host Name** (DNS endpoint).

#### Via the CLI

```bash
# Create the instance
databricks api post /api/2.0/database/instances \
  --json '{
    "name": "vibe-coding-workshop-lakebase",
    "capacity": "CU_1"
  }'

# Verify it is running and get the host
databricks api get /api/2.0/database/instances/vibe-coding-workshop-lakebase
```

The `read_write_dns` field in the response is your **Lakebase Host Name**.

**Parameters to record:**

| Parameter | Value |
|---|---|
| **Lakebase Instance Name** | `vibe-coding-workshop-lakebase` |
| **Lakebase Host Name** | `instance-<uuid>.database.cloud.databricks.com` |
| **Lakebase UC Catalog Name** | The UC catalog registered for this Lakebase instance (e.g., `vibe_coding_workshop_lakebase`) |

### 2.2 Create a Shared Serverless SQL Warehouse

Participants need a shared SQL Warehouse for running queries, creating metric views, TVFs, and Genie Spaces.

#### Via the UI

1. Navigate to **SQL Warehouses** > **Create SQL Warehouse**.
2. Configure:
   - **Name:** `vibe-coding-workshop-lakehouse`
   - **Type:** **Serverless**
   - **Size:** `Small` (sufficient for workshop-sized workloads)
   - **Auto Stop:** 15 minutes (to control cost)
3. Under **Permissions**, grant `CAN USE` to the `workshop-participants` group (or `account users` if all workspace users should have access).

#### Via the CLI

```bash
databricks warehouses create \
  --name "vibe-coding-workshop-lakehouse" \
  --cluster-size "Small" \
  --warehouse-type "SERVERLESS"
```

**Parameter to record:**

| Parameter | Value |
|---|---|
| **Default SQL Warehouse** | `vibe-coding-workshop-lakehouse` |

### 2.3 Create the Lakehouse Catalog and Grant Permissions

All participant-generated tables, schemas, pipelines, and Lakehouse objects are written to a shared catalog.

#### Step 1 — Create the catalog

```sql
CREATE CATALOG IF NOT EXISTS vibe_coding_workshop_catalog;
```

Or via CLI:

```bash
databricks unity-catalog catalogs create \
  --name "vibe_coding_workshop_catalog"
```

#### Step 2 — Grant permissions to all workspace users

The following grants ensure every participant can create their own schema and tables within the catalog. Adjust the principal (`account users` vs. your AD group) based on your security posture.

```sql
-- Allow all workspace users to use the catalog
GRANT USE CATALOG ON CATALOG vibe_coding_workshop_catalog TO `account users`;

-- Allow schema creation (each participant creates their own schema)
GRANT CREATE SCHEMA ON CATALOG vibe_coding_workshop_catalog TO `account users`;
```

> **Why `account users`?** This is the broadest grant and ensures no participant is blocked during the workshop. If you prefer tighter scoping, replace `account users` with your `workshop-participants` AD group.

Participants will create their own schemas during the workshop (e.g., `vibe_coding_workshop_catalog.john_doe`), and the SQL grants above automatically allow table creation within schemas they own.


**Parameter to record:**

| Parameter | Value |
|---|---|
| **Lakehouse Default Catalog** | `vibe_coding_workshop_catalog` |

### 2.4 Serverless General Compute Access (Budget Policy)

Participants need access to **Serverless General Compute** for running notebooks and jobs.

1. Enable Serverless compute for the workspace (if not already enabled).
2. **Create a budget policy** for workshop participants to control cost:
   - Navigate to **Compute** > **Budget Policies**.
   - Create a policy (e.g., `workshop-budget-policy`) with appropriate limits.
   - Assign the policy to the `workshop-participants` group (or `account users`).
3. Grant permission to create and use Serverless compute.

---

# Chapter 3: Model Serving & App Deployment

**Owner:** Workspace Admin  
**Estimated Time:** 30 min

### 3.1 Verify the LLM Endpoint

The workshop app calls an LLM endpoint for prompt generation and AI features. The default is `databricks-claude-3-7-sonnet` (pay-per-token, no provisioning required).

#### Verify the endpoint exists

```bash
databricks serving-endpoints get databricks-claude-3-7-sonnet
```

If the endpoint is not available, check that **Foundation Model APIs** (pay-per-token) are enabled in your workspace:

1. Navigate to **Workspace Settings** > **Model Serving**.
2. Ensure pay-per-token endpoints are enabled.

#### Grant access to the App's service principal

After the app is deployed (Step 3.2), the app's service principal needs permission to call the endpoint. This is handled automatically by the deploy script. If you need to grant it manually:

```bash
# Get the app's service principal ID
databricks apps get <app-name> --output json | python3 -c "import sys,json; print(json.load(sys.stdin).get('service_principal_client_id',''))"

# Grant CAN_QUERY on the serving endpoint
databricks api put /api/2.0/permissions/serving-endpoints/<endpoint-id> \
  --json '{"access_control_list": [{"service_principal_name": "<sp-name>", "all_permissions": [{"permission_level": "CAN_QUERY"}]}]}'
```

**Parameter to record:**

| Parameter | Value |
|---|---|
| **Model Serving Endpoint** | `databricks-claude-3-7-sonnet` |



---

# Chapter 4: Authentication

**Owner:** Admin + Participants  
**Estimated Time:** 15 min

The Databricks CLI is the primary tool for authenticating and interacting with the workspace. There are multiple authentication methods — **OAuth (U2M)** is the preferred enterprise approach, with **PAT** as a fallback.

### 4.1 Authentication Options Overview

| Method | Security | Recommended For | Token Lifetime |
|---|---|---|---|
| **OAuth U2M** (preferred) | Strongest — no long-lived tokens | Enterprise workshops, SSO-enabled workspaces | Session-based, auto-refreshes |
| **Personal Access Token (PAT)** | Moderate — static token | Quick setup, corporate environments where OAuth browser flow is restricted | Configurable (7–90 days) |
| **Azure AD / Google OAuth** | Strongest — cloud-native | Cloud-specific workshops | Session-based |

### 4.2 Option A — OAuth (U2M) — Preferred

OAuth User-to-Machine (U2M) is the recommended approach. It opens a browser for SSO login and manages token refresh automatically.

```bash
databricks auth login --host https://<your-workspace-url>
```

When prompted:
1. A browser window opens for SSO authentication.
2. Complete the login flow in the browser.
3. Return to the terminal — the CLI is now authenticated.

Verify authentication:

```bash
databricks auth env
```

**Expected output:**

```
DATABRICKS_HOST=https://<your-workspace-url>
```

> **Note for admins:** OAuth U2M requires that the workspace has SSO/OIDC configured. Most enterprise workspaces have this by default. If participants cannot complete the browser flow (e.g., headless environments), fall back to PAT.

### 4.3 Option B — Personal Access Token (PAT) — Alternative

Use this method if OAuth is unavailable or the browser flow is restricted in your environment.

#### Step 1 — Generate a PAT

1. Log in to your Databricks workspace in a browser.
2. Click your **user icon** (top-right) > **Settings**.
3. Navigate to **Developer** > **Access Tokens**.
4. Click **Generate New Token**.
5. Comment: `workshop-token`, Expiration: `7 days`.
6. **Copy the token immediately** — it cannot be retrieved later.

#### Step 2 — Configure the CLI

```bash
databricks configure --profile DEFAULT
```

| Prompt | Value |
|---|---|
| **Databricks Host** | `https://<your-workspace-url>` |
| **Personal Access Token** | The token from Step 1 |

#### Step 3 — Verify

```bash
databricks auth env --profile DEFAULT
```

### 4.4 Option C — Cloud-Native Authentication

| Cloud | Method | Command |
|---|---|---|
| **Azure** | Azure AD (Entra ID) | `az login && databricks auth login --host <url>` |
| **GCP** | Google OAuth | `gcloud auth login && databricks auth login --host <url>` |
| **AWS** | OAuth U2M (default) | See Option A above |

### 4.5 Validate Connectivity

Regardless of method, confirm the CLI is working:

```bash
# Check authenticated identity
databricks current-user me

# List workspace contents
databricks workspace list /
```

You should see top-level workspace folders (`/Repos`, `/Users`, `/Shared`).

> **If authentication fails:**
> - Double-check the workspace URL (no trailing slash).
> - For OAuth: ensure SSO is configured and the browser flow completes.
> - For PAT: regenerate the token and reconfigure.
> - Ensure AD group membership has been provisioned (Chapter 1).

---

# Chapter 5: Admin Cleanup (Post-Workshop)

**Owner:** Workspace Admin / Account Admin  
**Estimated Time:** 15–30 min

After the workshop concludes, clean up resources to avoid ongoing costs and clutter. Choose the approach that matches how you set up the workshop.

### Option A — Delete the Entire Workspace (Fastest — If You Created a Dedicated Workspace)

If you created a workspace specifically for the workshop (Chapter 1, Option A), the cleanest approach is to delete it entirely:

1. Go to the **Databricks Account Console** > **Workspaces**.
2. Select the workshop workspace.
3. Click **Delete Workspace**.
4. Confirm deletion.

This removes all resources — compute, catalogs, Lakebase instances, apps, and participant data — in one action.

### Option B — Selective Resource Cleanup (If Using a Shared Workspace)

If you used an existing workspace, remove workshop-specific resources individually:

#### 1. Delete the Workshop App

```bash
databricks apps delete <app-name>
```

#### 2. Delete the Lakebase Instance

```bash
databricks api delete /api/2.0/database/instances/<lakebase-instance-name>
```

#### 3. Stop/Delete the SQL Warehouse

```bash
# Stop it (to halt billing)
databricks warehouses stop <warehouse-id>

# Or delete it entirely
databricks warehouses delete <warehouse-id>
```

#### 4. Drop the Workshop Catalog

```sql
-- First, drop all schemas created by participants
-- (list them first to review)
SHOW SCHEMAS IN vibe_coding_workshop_catalog;

-- Drop the catalog and all contents
DROP CATALOG IF EXISTS vibe_coding_workshop_catalog CASCADE;
```

#### 5. Remove the AD Group / Revoke Permissions

```sql
-- Revoke catalog permissions (if catalog was not dropped)
REVOKE ALL PRIVILEGES ON CATALOG vibe_coding_workshop_catalog FROM `workshop-participants`;
```

Then remove the `workshop-participants` group from the workspace via:
- **Workspace Settings** > **Identity and access** > **Groups** > Delete group
- Or via the Account Console if it's an account-level group

#### 6. Remind Participants to Revoke PATs

If participants authenticated via PAT, remind them to delete their tokens:
- **User Settings** > **Developer** > **Access Tokens** > Delete the workshop token

### Option C — Deactivate Participants Only (Keep Infrastructure for Future Workshops)

If you plan to rerun the workshop:

1. **Remove participants** from the AD group (revokes workspace access).
2. **Stop** the SQL Warehouse and Lakebase instance (stops billing but preserves configuration).
3. **Drop participant schemas** but keep the catalog:

```sql
-- List and drop individual participant schemas
SHOW SCHEMAS IN vibe_coding_workshop_catalog;
DROP SCHEMA IF EXISTS vibe_coding_workshop_catalog.<participant_schema> CASCADE;
```

4. **Re-seed the app database** before the next workshop:

```bash
cd files/files
./scripts/setup-lakebase.sh --recreate --yes
```

---

## Troubleshooting

| Issue | Resolution |
|---|---|
| **Cannot log in to workspace** | Confirm AD group membership with your admin. Allow up to 24 hours for provisioning. |
| **"Permission denied" on catalog** | Admin needs to run the `GRANT` statements from Chapter 2.3. |
| **Serverless compute not available** | Admin needs to enable Serverless compute and assign a budget policy (Chapter 2.4). |
| **Lakebase instance not RUNNING** | Check instance state: `databricks api get /api/2.0/database/instances/<name>`. Wait for provisioning or recreate. |
| **LLM endpoint not found** | Ensure Foundation Model APIs (pay-per-token) are enabled in workspace settings (Chapter 3.1). |
| **Workshop app fails to start** | Check app logs: `databricks apps logs <app-name>`. Verify Lakebase is running and the app resource link is configured. |
| **OAuth browser flow fails** | Check SSO/OIDC configuration. Fall back to PAT authentication (Chapter 4.3). |

---

## Need Help?

If you run into issues completing these prerequisites, reach out to the Databricks workshop organizers **before** the session so we can troubleshoot together. We want everyone ready to build on day one.

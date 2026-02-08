# Data Product Accelerator — Prerequisites Guide

> **Purpose:** This document outlines everything participants need to have in place **before** the workshop begins. Completing these steps ahead of time ensures you can focus on building, not troubleshooting setup issues during the session.
>
> **How the workshop runs:** The workshop is delivered as a **Databricks App** backed by **Lakebase** (managed PostgreSQL) that guides participants through the framework step by step — from Gold layer design through GenAI agent deployment. Participants use an AI-powered IDE alongside the App to build production-grade Databricks solutions.

---

## Overview

| # | Prerequisite | Owner | Estimated Time |
|---|---|---|---|
| 1 | Workspace access for participants | Admin | 1–2 days (AD group provisioning) |
| 2 | Unity Catalog access with schema creation privileges | Admin | 30 min |
| 3 | Serverless SQL Warehouse access | Admin | 15 min |
| 4 | Serverless General Compute access (budget policy) | Admin | 15 min |
| 5 | Databricks Apps enabled with Lakebase access | Admin | 30 min |
| 6 | Install an AI-powered IDE | Participant | 15 min |
| 7 | Provision IDE licenses / AI model access | Admin + Participant | Varies |
| 8 | Access to Claude Sonnet 4.5 (or higher) | Participant | 10 min |
| 9 | Install the Databricks CLI | Participant | 10 min |
| 10 | Authenticate to the workspace and validate connectivity | Participant | 10 min |

---

## Admin Prerequisites (complete before the workshop)

These steps are typically performed by a **Workspace Admin** or **Account Admin** in advance.

### 1. Workspace Access for Participants

Participants must be able to log in to the Databricks workspace used for the workshop.

- **Recommended approach:** Create a dedicated **AD (Active Directory) group** (e.g., `workshop-participants`) and assign all attendees to it.
- Grant the AD group access to the target Databricks workspace.
- Verify that each participant can successfully log in to the workspace URL.

> **Tip:** Send participants the workspace URL and ask them to confirm login access at least **48 hours** before the workshop.

---

### 2. Unity Catalog Access — Catalog + Schema Creation Privileges

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

### 3. Serverless SQL Warehouse Access

Participants need access to a **Serverless SQL Warehouse** for running queries, creating metric views, TVFs, and Genie Spaces.

- Create a shared Serverless SQL Warehouse (e.g., `Workshop SQL Warehouse`) or use an existing one.
- Grant the AD group `CAN USE` permission on the warehouse.
- Ensure the warehouse is set to **Serverless** (not Classic or Pro).

> **Sizing guidance:** A `Small` Serverless SQL Warehouse is typically sufficient for workshop-sized workloads.

---

### 4. Serverless General Compute Access (Budget Policy)

Participants need access to **Serverless General Compute** for running notebooks and jobs.

- Enable Serverless compute for the workspace (if not already enabled).
- **Create a budget policy** for workshop participants to control cost:
  - Navigate to **Compute > Budget Policies** in the workspace.
  - Create a policy (e.g., `workshop-budget-policy`) with appropriate limits.
  - Assign the policy to the `workshop-participants` AD group.
- Grant the AD group permission to create and use Serverless compute.

> **Important:** Without a budget policy, participants may not be able to launch Serverless compute. Verify this is configured before the workshop.

---

### 5. Databricks Apps Enabled with Lakebase Access

The workshop is delivered as a **Databricks App** that guides participants through the framework step by step. This requires Databricks Apps and Lakebase (managed PostgreSQL) to be enabled in the workspace.

#### 5a. Enable Databricks Apps

- Navigate to **Workspace Settings > Compute > Databricks Apps**.
- Ensure Apps are **enabled** for the workspace.
- Grant the AD group the **Consumer** entitlement so participants can access deployed Apps:
  - Navigate to **Workspace Settings > Identity and access > Groups**.
  - Select the `workshop-participants` group.
  - Under **Entitlements**, enable **Consumer**.

> **Note:** Databricks Apps run on dedicated Serverless compute. No additional cluster configuration is required.

#### 5b. Enable Lakebase (Managed PostgreSQL)

The workshop App uses **Lakebase** as its backend database for tracking participant progress, storing session state, and managing the guided workflow.

- Ensure Lakebase is **enabled** for the workspace:
  - Navigate to **Workspace Settings > Compute > Lakebase**.
  - Enable the feature if not already active.
- Grant the AD group permission to create and access Lakebase databases:

```sql
-- Grant Lakebase usage (if using Unity Catalog-governed access)
GRANT USE CATALOG ON CATALOG workshop TO `workshop-participants`;
GRANT CREATE SCHEMA ON CATALOG workshop TO `workshop-participants`;
```

> **Why Lakebase:** The workshop App uses a managed PostgreSQL instance (Lakebase) to persist application state, guide participants through each stage, and store configuration. This eliminates the need for external database provisioning.

#### 5c. Verify App Deployment Readiness

Before the workshop, the organizer should deploy the workshop App and verify it starts successfully:

```bash
# Deploy the workshop app (run from the project root)
databricks apps create --name workshop-guide --profile DEFAULT

# Verify the app is running
databricks apps get --name workshop-guide --profile DEFAULT
```

Participants should be able to access the App URL from their browser once it's deployed.

> **Sizing guidance:** Lakebase instances for workshop use are lightweight — the default configuration is sufficient for up to 50 concurrent participants.

---

## Participant Prerequisites (complete before the workshop)

These steps must be completed by **each participant** on their own machine.

### 6. Install an AI-Powered IDE

Install one of the following AI-powered IDEs on your machine:

| IDE | Download Link | Notes |
|---|---|---|
| **Cursor** (recommended) | [cursor.com](https://www.cursor.com/) | Built-in AI coding assistant |
| **Windsurf** | [windsurf.com](https://windsurf.com/) | AI-native code editor |
| **VS Code + GitHub Copilot** | [code.visualstudio.com](https://code.visualstudio.com/) | Requires Copilot extension |

> **Corporate environments:** If your organization restricts software installation, submit a software exception request through your IT portal before the workshop.

---

### 7. Provision IDE Licenses and AI Model Access

Depending on your chosen IDE, you may need to provision licenses:

| IDE | License Requirement |
|---|---|
| **Cursor** | Pro or Business plan recommended for full AI features |
| **Windsurf** | Check your organization's SSO portal for access |
| **VS Code + Copilot** | GitHub Copilot Individual or Business subscription |

**Verify your license is active** by opening the IDE and confirming the AI assistant responds to prompts.

---

### 8. Access to Claude Sonnet 4.5 or Higher

The workshop leverages advanced AI models for code generation. You need access to **Claude Sonnet 4.5** (or higher, such as Claude Opus) through your IDE.

- **Cursor:** Go to **Settings > Models** and ensure Claude Sonnet 4.5 (or higher) is enabled.
- **Windsurf:** Verify model availability in your plan settings.
- **VS Code + Copilot:** Copilot uses its own models; ensure your subscription is active.

> **Why Claude Sonnet 4.5+:** The workshop's agent skills and prompts are optimized for advanced reasoning capabilities. Lower-tier models may produce less reliable results.

---

### 9. Install the Databricks CLI

The Databricks CLI is required for authentication and deploying Asset Bundles.

#### macOS (Homebrew)

```bash
brew tap databricks/tap
brew install databricks
```

#### Windows (WinGet)

```powershell
winget install Databricks.DatabricksCLI
```

#### Linux (curl)

```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

#### Verify installation

```bash
databricks --version
```

You should see output like `Databricks CLI v0.x.x`. Any recent version is acceptable.

> **Troubleshooting:** If you encounter security-related installation issues in a corporate environment, submit a software exception request through your IT portal.

---

### 10. Authenticate to the Workspace and Validate Connectivity

Once the CLI is installed, configure it to connect to your workshop workspace.

#### Step 10a: Generate a Personal Access Token (PAT)

1. Log in to your Databricks workspace in a browser.
2. Click your **user icon** (top-right corner) > **Settings**.
3. Navigate to **Developer** > **Access Tokens**.
4. Click **Generate New Token**.
5. Provide a comment (e.g., `workshop-token`) and set an expiration (e.g., 7 days).
6. **Copy the token immediately** — you won't be able to see it again.

#### Step 10b: Configure the Databricks CLI

Open a terminal in your IDE and run:

```bash
databricks configure --profile DEFAULT
```

When prompted, enter:

| Prompt | Value |
|---|---|
| **Databricks Host** | `https://<your-workspace-url>` (provided by workshop organizer) |
| **Personal Access Token** | The token you generated in Step 10a |

#### Step 10c: Validate Connectivity

Run the following command to confirm authentication:

```bash
databricks auth env --profile DEFAULT
```

**Expected output** (values will vary):

```
DATABRICKS_HOST=https://<your-workspace-url>
DATABRICKS_TOKEN=dapi********************************
```

Additionally, verify you can list workspace contents:

```bash
databricks workspace list / --profile DEFAULT
```

You should see a list of top-level workspace folders (e.g., `/Repos`, `/Users`, `/Shared`).

> **If authentication fails:**
> - Double-check the workspace URL (no trailing slash).
> - Regenerate your PAT and reconfigure.
> - Ensure your AD group membership has been provisioned (Step 1).
> - If using OAuth instead of PAT, refer to the [Databricks CLI authentication docs](https://docs.databricks.com/en/dev-tools/cli/authentication.html).

---

## Pre-Workshop Checklist

Use this checklist to confirm everything is ready:

### Admin Checklist

- [ ] AD group created and all participants added
- [ ] Participants can log in to the workspace
- [ ] Workshop catalog created with `CREATE SCHEMA` privileges granted
- [ ] Serverless SQL Warehouse provisioned and accessible
- [ ] Serverless General Compute enabled with budget policy assigned
- [ ] Databricks Apps enabled in workspace settings
- [ ] Lakebase enabled in workspace settings
- [ ] AD group granted Consumer entitlement
- [ ] Workshop App deployed and accessible at its URL

### Participant Checklist

- [ ] AI-powered IDE installed and licensed
- [ ] Claude Sonnet 4.5 (or higher) model accessible in IDE
- [ ] Databricks CLI installed (`databricks --version` works)
- [ ] CLI authenticated (`databricks auth env --profile DEFAULT` returns valid credentials)
- [ ] Workspace accessible (`databricks workspace list / --profile DEFAULT` returns results)
- [ ] Workshop App URL loads successfully in browser

---

## Troubleshooting Common Issues

| Issue | Resolution |
|---|---|
| **Cannot log in to workspace** | Confirm AD group membership with your admin. Allow up to 24 hours for provisioning. |
| **"Permission denied" on catalog** | Admin needs to run the `GRANT` statements from Step 2. |
| **Serverless compute not available** | Admin needs to enable Serverless compute and assign a budget policy (Step 4). |
| **Databricks Apps not available** | Admin needs to enable Apps in Workspace Settings > Compute > Databricks Apps (Step 5). |
| **Lakebase not available** | Admin needs to enable Lakebase in Workspace Settings > Compute > Lakebase (Step 5). |
| **Workshop App fails to start** | Check that Lakebase is enabled, the AD group has the Consumer entitlement, and the app was deployed with correct permissions. Review app logs via `databricks apps get-logs --name workshop-guide`. |
| **CLI install blocked by corporate policy** | Submit a software exception request through your IT portal. |
| **`databricks auth env` returns an error** | Regenerate your PAT and reconfigure with `databricks configure --profile DEFAULT`. |
| **IDE AI features not working** | Verify your license/subscription is active and the correct model is selected. |

---

## Need Help?

If you run into issues completing these prerequisites, please reach out to the workshop organizers **before** the session so we can troubleshoot together. We want everyone ready to build on day one.

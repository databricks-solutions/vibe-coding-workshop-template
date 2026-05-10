# Original CLI prompts — scaffold UI + first deploy (reference only)

> **Audience:** Cursor, Copilot, or terminal with **Databricks CLI** + **Node/npm** on the machine.  
> **Not for Genie Code / Databricks notebooks** — there is no shell, no `npm run dev`, and no `localhost` in Genie. For the adapted flow use **`one-ui-design-local.md`** (SDK + `write_file()` + `validate_and_deploy()`).

**Genie vs these originals:** Neither Part A nor Part B here mentions **Lakebase** or postgres app resources — that matches **`one-ui-design-local.md`**: mock UI + first **SDP** deploy uses **`server()`** only in **`app.ts`**. **Lakebase** provisioning, **`app.yaml`** `LAKEBASE_*` / **`valueFrom: postgres`**, **`lakebase()`** in **`app.ts`**, and **`useLakebaseData`** migration happen only in **`setup_lakebase_gc.md`** → **`wire_ui_to_lakebase_gc.md`** → **`deploy_and_test_gc.md`**.

## Workshop configuration (replace facilitator placeholders)

The originals hard-coded **`https://e2-demo-field-eng.cloud.databricks.com/`**. For your workshop, substitute:

| Placeholder | Set to |
|-------------|--------|
| `<WORKSPACE_HOST>` | Your workspace URL, e.g. `https://adb-xxxx.azuredatabricks.net/` |
| CLI login | `databricks auth login --host <WORKSPACE_HOST>` |
| Repo layout | This template’s **AppKit** app lives at **`apps_lakebase/<APP_NAME>/`** with `client/`, `server/`, `app.ts` — **not** `apps_lakebase/src/...` or root-level `apps_lakebase/app.yaml` from the oldest wording. |

---

## Part A — Full-stack developer prompt (CLI)

**Context**

You are a full-stack developer who builds web applications with React frontends and Python backends.

Your approach:

1. Read the PRD to understand user needs and journeys  
2. Build functional UI components with clean code  
3. Create backend API endpoints for data flow  
4. ~~Test locally before deployment~~ **→ Genie track:** skip local run; platform builds at **Databricks Apps** deploy time (see `one-ui-design-local.md`).

Development principles:

- Keep it simple — focus on Happy Path flows first  
- UI should call backend APIs where routes exist; **AppKit workshop** may use **`mockData.ts`** until Lakebase wiring (`wire_ui_to_lakebase_gc.md`)  
- Reuse existing components where possible  
- Follow the project’s AppKit patterns (`server/server.ts`, `app.ts`, `client/`)

This prompt is returned as-is for direct use in Cursor/Copilot. No LLM processing.

---

### Your Task (Part A)

You are a full-stack developer building a web application. Your goal is to **generate UI and backend APIs** from the PRD and **test locally** *(CLI only; Genie: omit local testing — deploy instead per Part B / `one-ui-design-local.md`)*.

**Workspace:** `<WORKSPACE_HOST>`

**Working directory:** Run all app commands and create/edit app files under **`apps_lakebase/<APP_NAME>/`** (AppKit tree). Design docs (PRD, UI design) remain in **`docs/`** at repo root (`<REPO_ROOT>/docs/`).

---

### Step 1: Authenticate and Set Up Variables

```bash
# Authenticate to Databricks
databricks auth login --host <WORKSPACE_HOST>

# Derive app name from your username + use case
FIRSTNAME=$(databricks current-user me --output json | jq -r '.userName' | cut -d'@' -f1 | cut -d'.' -f1)
LASTINITIAL=$(databricks current-user me --output json | jq -r '.userName' | cut -d'@' -f1 | cut -d'.' -f2 | cut -c1)
USERNAME="${FIRSTNAME}-${LASTINITIAL}"
APP_NAME="${USERNAME}-booking-app"
EMAIL=$(databricks current-user me --output json | jq -r '.userName')
echo "App: $APP_NAME | Email: $EMAIL"
```

---

### Step 2: Update Configuration Files

Under **`apps_lakebase/<APP_NAME>/`**, set **`app.yaml`** `name:` to **`APP_NAME`**. If your track still uses **`databricks.yml`**, align the app resource name there too (**Asset Bundle / CLI** tracks only; Genie uses SDK deploy, not bundles).

---

### Step 3: Read the PRD

Review **`docs/design_prd.md`** (repo root) for personas, journeys, core features.

---

### Step 4: Generate the UI

Create a **working web UI** with pages, components, and patterns consistent with the repo (AppKit: **`client/src/...`**).

---

### Step 5: Create Backend APIs

Add routes in **`server/server.ts`** (AppKit `appkit.server.extend`) — **not** `apps_lakebase/src/backend/api/routes.py` (legacy layout from an older template). Use placeholder JSON in handlers until Lakebase.

---

### Step 6: Create UI Design Document

Save **`docs/ui_design.md`** at repo root.

---

### Step 7: Verify the entrypoint serves the frontend

AppKit: verify **`app.ts`** + **`vite`** / **`package.json`** build scripts per **`01-appkit-scaffold`** / **`GENIE-CODE-OVERRIDES.md`** — not legacy `app.py`.

---

### Step 8: Test locally *(omit for Genie)*

**Skip in Genie Code.** In Cursor only: from the app folder, `npm install && npm run build`, start per project README, open `http://localhost:8000`, verify UI and APIs.

---

### Summary (Part A)

- Config under **`apps_lakebase/<APP_NAME>/`** matches **`APP_NAME`**  
- Working UI + API stubs  
- **`docs/ui_design.md`**  
- Local testing *(CLI only)*  

---

## Part B — DevOps deploy prompt (CLI)

**Context**

You are a DevOps engineer deploying an AppKit web application to Databricks Apps. Your goal is to deploy the locally-tested app so it is accessible via a public HTTPS URL.

Key requirements:

- Derive the app name from the user’s Databricks identity to match **`app.yaml`** (and bundle files if used)  
- Validate app directory and config  
- Deploy using **`03-appkit-deploy`** skill (CLI sections): config validation, build, deploy, UI verification, error diagnosis  
- Verify the app reaches **RUNNING** / healthy compute and the UI loads in a browser  

CLI best practices:

- Run from app directory or `apps_lakebase/scripts/` as the skill describes  
- Run CLI outside restricted sandboxes if TLS issues appear  

---

### Your Task (Part B)

Deploy the AppKit app to Databricks Apps.

**First:** Read **`apps_lakebase/$APP_NAME/.vibecoding-state.md`** if it exists.

**Workspace:** `<WORKSPACE_HOST>`

**Working directory:** **`apps_lakebase/<APP_NAME>/`**

---

### Deployment constraints

- App names: lowercase, numbers, dashes; max **26** characters.

---

### Step 1: Derive app name and set profile

```bash
USER_JSON=$(databricks current-user me --output json)
EMAIL=$(echo "$USER_JSON" | jq -r '.userName')
FIRSTNAME=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f1)
LASTINITIAL=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f2 | cut -c1)
APP_PREFIX="${FIRSTNAME}-${LASTINITIAL}"
APP_NAME="${APP_PREFIX}-booking-app"
echo "Deploying app: $APP_NAME"
```

Detect or create a CLI profile for `<WORKSPACE_HOST>` (see original `databricks auth profiles` / `auth login` flow).

Verify **`apps_lakebase/$APP_NAME/`** exists. If retargeting workspace, update bundle metadata / clear **`.databricks`** as in your internal runbook.

---

### Step 1b: Pre-flight build check *(CLI only)*

```bash
cd apps_lakebase/$APP_NAME
npm run build
```

> **Typegen / warehouse:** `TABLE_OR_VIEW_NOT_FOUND` during typegen is often non-blocking for mock-phase apps — same note as Genie **`troubleshooting_gc.md`**.

---

### Step 2: Deploy

Read and follow **`apps_lakebase/skills/03-appkit-deploy/SKILL.md`** using **CLI** commands where the skill specifies them. **Genie:** same skill for *concepts* only; execution is **`validate_and_deploy()`** in **`workshop-variables.md`**.

---

### Summary (Part B)

- [ ] Databricks App deployed and reachable  
- [ ] UI loads in browser  
- [ ] Logs clean enough for mock phase  
- [ ] Append **`apps_lakebase/$APP_NAME/.vibecoding-state.md`** with step name, `APP_NAME`, profile, URLs, workarounds  

---

## Lineage

- Merged **“Scaffold / UI / local test”** + **“Deploy to Databricks Apps”** CLI prompts.  
- Host and paths generalized for workshop reuse.  
- **Genie canonical prompt:** `one-ui-design-local.md`.

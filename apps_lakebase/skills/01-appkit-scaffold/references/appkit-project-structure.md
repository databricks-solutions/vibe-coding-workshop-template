# AppKit Project Structure and Development Workflow

**Upstream docs (always check for latest):** https://databricks.github.io/appkit/docs/development/project-setup
Also consult the live AppKit docs: `npx @databricks/appkit docs "project setup"`
The information below may be outdated. Prefer upstream when available.

## Canonical Layout

After scaffolding with `databricks apps init`, an AppKit project has this structure:

```
my-app/
├── server/
│   ├── server.ts          # Backend entry point (AppKit createApp + plugins)
│   └── .env               # Local dev env vars (do NOT commit)
├── client/
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx         # Main React component (start here)
│       └── appKitTypes.d.ts  # Auto-generated query types
├── config/
│   └── queries/
│       └── *.sql           # SQL query files (key = filename without .sql)
├── tests/
│   └── smoke.spec.ts      # Smoke test (update selectors for your app)
├── app.yaml                # Databricks Apps deployment config
├── package.json
├── tsconfig.json
└── databricks.yml          # Bundle config (auto-generated)
```

## Key Files to Modify

| Task | File |
|------|------|
| Build UI | `client/src/App.tsx` |
| Add SQL query | `config/queries/<name>.sql` |
| Add backend plugin | `server/server.ts` |
| Add API endpoint | `server/server.ts` (tRPC or Express extend) |
| Fix smoke test | `tests/smoke.spec.ts` |

## package.json Scripts

```json
{
  "scripts": {
    "dev": "NODE_ENV=development tsx watch server/server.ts",
    "build": "npm run build:server && npm run build:client",
    "build:server": "tsdown --out-dir build server/server.ts",
    "build:client": "tsc -b && vite build --config client/vite.config.ts",
    "start": "node build/index.mjs",
    "typegen": "appkit typegen"
  }
}
```

## Development Workflow

### 1. Start Development

```bash
cd <app-name>
npm install
npm run dev
```

The dev server starts on `http://localhost:8000` with:
- Express backend
- Vite dev middleware for the frontend (hot reload)

### 2. Development Loop (Recommended Order)

1. Create SQL files in `config/queries/`
2. Run `npm run typegen` — verify all queries show checkmarks
3. Read `client/src/appKitTypes.d.ts` to see generated types
4. Write `client/src/App.tsx` using the generated types
5. Update `tests/smoke.spec.ts` selectors for your app

**Do NOT write UI code before running typegen.** Types won't exist and you'll get compilation errors.

### 3. Build and Validate

```bash
npm run build
databricks apps validate
```

### 4. Deploy

```bash
databricks apps deploy --profile <PROFILE>
```

## Server Entry Point Pattern

Minimal server with no plugins:

```typescript
import { createApp, server } from "@databricks/appkit";

await createApp({
  plugins: [server()],
});
```

With plugins:

```typescript
import { createApp, server, analytics, lakebase, genie, files } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    analytics(),
    lakebase(),
    genie(),
    files(),
  ],
});
```

Custom Express routes (use `autoStart: false`):

```typescript
import { createApp, server } from "@databricks/appkit";

const appkit = await createApp({
  plugins: [server({ autoStart: false })],
});

appkit.server.extend((app) => {
  app.get("/custom", (_req, res) => res.json({ ok: true }));
});

await appkit.server.start();
```

## Server Plugin Defaults

- **Port:** `process.env.DATABRICKS_APP_PORT || 8000`
- **Host:** `process.env.FLASK_RUN_HOST || "0.0.0.0"`
- **Health check:** `GET /health` returns `{ "status": "ok" }`
- **Frontend (dev):** Vite middleware from `client/`
- **Frontend (prod):** Static files from `client/dist/`

## Live Documentation

Always consult the official docs for the latest API details:

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # specific topic
npx @databricks/appkit docs --full       # all entries
```

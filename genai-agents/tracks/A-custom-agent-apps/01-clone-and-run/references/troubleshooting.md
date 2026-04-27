# Troubleshooting quickstart and local dev server

Use this reference when `uv run quickstart` or `uv run start-app` fails, or
when the chat UI or `/invocations` endpoint does not behave as expected.

## Common errors and fixes

| Issue | Fix |
|-------|-----|
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `databricks auth token` fails | Run `databricks configure` to set up authentication |
| Port 8000 already in use | Kill the existing process: `lsof -ti:8000 \| xargs kill` |
| `ModuleNotFoundError` on start | Run `uv run quickstart` to install dependencies |
| Chat UI shows "connection refused" | Ensure the server is running on `0.0.0.0:8000`, not only bound to `127.0.0.1:8000` if you changed defaults |
| LLM endpoint errors | Verify the serving endpoint name in `.env` or `config.yml` exists in your workspace |

## Agent does not respond (server seems up)

If `uv run start-app` appears healthy but the UI or `curl` to `/invocations`
gets no useful reply:

1. Confirm `uv run start-app` is still running and watch the terminal for tracebacks or HTTP errors.
2. Confirm `.env` is populated; compare keys and shapes with `.env.example`.
3. Confirm Databricks CLI auth: `databricks auth token` succeeds for the profile quickstart used.

## Skipping quickstart

Running `uv run start-app` without running `uv run quickstart` first often fails
because dependencies are missing and `.env` was never created. Always run
quickstart once per machine/clone before `start-app`.

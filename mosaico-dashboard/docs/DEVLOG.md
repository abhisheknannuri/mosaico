# Dev log

One line per finished task. Newest at the bottom.

| Date | Task | Summary |
|---|---|---|
| 2026-10-17 | (pre-sprint) | Created docs folder, backlog, ADR-0001…0004. |
| 2026-10-17 | D-01 | Poetry project (py3.12 venv), editable SDK via `dev_setup.sh`, ruff pre-commit hooks, placeholder `/healthz`, `Dockerfile.mosaico-dashboard` (non-editable SDK, non-root), `dashboard-compose.yml` with `development`/`production` profiles reusing the existing catalog volume. Gotcha: Docker-injected HTTP proxy broke gRPC from the container → `NO_PROXY` (ADR-0005). |
| 2026-10-17 | D-02 | pyright + pytest config, `/healthz` test, `scripts/check.sh`. Gotchas: system Node v12 crashes pyright → `pyright[nodejs]`; Starlette TestClient wants `httpx2`. |
| 2026-10-17 | D-03 | Layer packages (`domain`, `gateway`, `services`, `web/pages`, `web/api`), `import-linter` contracts in `check.sh`, `docs/architecture.md` with diagrams, ADR-0006. |
| 2026-10-17 | D-04 | Settings (`DASHBOARD_*`, `.env`), console logging in SDK format with optional Rich, `poetry run mosaico-dashboard` (also Docker CMD), ADR-0007. Gotcha: with reload, uvicorn runs the app in a child process, so logging is set up in both `run()` and `main.py`. |
| 2026-10-17 | D-04 | Renamed `DASHBOARD_LOG_PRETTY` → `DASHBOARD_LOG_FORMAT=plain|pretty` (mirrors `MOSAICOD_LOG_FORMAT`); invalid values rejected at startup. |

# Dev log

One line per finished task. Newest at the bottom.

| Date | Task | Summary |
|---|---|---|
| 2026-10-17 | (pre-sprint) | Created docs folder, backlog, ADR-0001…0004. |
| 2026-10-17 | D-01 | Poetry project (py3.12 venv), editable SDK via `dev_setup.sh`, ruff pre-commit hooks, placeholder `/healthz`, `Dockerfile.mosaico-dashboard` (non-editable SDK, non-root), `dashboard-compose.yml` with `development`/`production` profiles reusing the existing catalog volume. Gotcha: Docker-injected HTTP proxy broke gRPC from the container → `NO_PROXY` (ADR-0005). |
| 2026-10-17 | D-02 | pyright + pytest config, `/healthz` test, `scripts/check.sh`. Gotchas: system Node v12 crashes pyright → `pyright[nodejs]`; Starlette TestClient wants `httpx2`. |
| 2026-10-17 | D-03 | Layer packages (`domain`, `gateway`, `services`, `web/pages`, `web/api`), `import-linter` contracts in `check.sh`, `docs/architecture.md` with diagrams, ADR-0006. |

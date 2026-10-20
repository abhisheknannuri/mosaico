# Rules for working on mosaico-dashboard

## Workflow
- Pair-programming with Abhishek: one backlog task at a time (`docs/BACKLOG.md`), in order.
- Never commit or push unless asked. Commits go to the fork `abhisheknannuri/mosaico`, branch `AN/FastAPI_Dashboard`.
- After a task: update `docs/BACKLOG.md`, add a line to `docs/DEVLOG.md`, write an ADR in `docs/decisions/` if a decision was made.
- Testing: mosaicod runs via the compose `development` profile; run and test the dashboard from the local venv (`bash ./scripts/check.sh`). Don't build/test the dashboard container unless asked.

## Simplicity
- Don't over-engineer. Scripts and configs are plain and readable: no dynamic path resolution, env-var defaults or fallbacks unless actually needed.
- Assume the documented setup (README) was followed; don't code around other setups.

## Comments
- Code/config comments: short, neutral, describe what something is or does (e.g. one line per compose service or profile).
- No explanatory or rationale comments aimed at the developer ("NOTE: on purpose…", warnings, history). Rationale goes in `docs/decisions/`, explained in chat.

## Stack facts
- SDK installed with `pip install -e ../mosaico-sdk-py` in dev (`scripts/dev_setup.sh`), non-editable in Docker. Not in `pyproject.toml`.
- Lint/format: ruff, same config as `mosaico-sdk-py`. Hooks in repo-root `.pre-commit-config.yaml`.
- Layers `(web | jobs) → services → (gateway | db) → domain`, enforced by import-linter (`docs/architecture.md`). Only `gateway/` imports `mosaicolabs`. Create folders only when a task needs them.
- Keep `docs/architecture.md` up to date when structure changes.
- Gateway, services and page routes are synchronous (`def`), because the SDK blocks (ADR-0012).
- UI: follow `docs/ui.md` (component macros, tokens, no page-specific CSS); screenshot-review every UI change.
- Tests: follow `docs/architecture.md` §5 (FakeGateway not mocks, fixtures in conftest, hermetic, order-independent).
- CI: `.github/workflows/dashboard-ci.yml` runs `scripts/check.sh` (Py 3.10, 3.13) + Docker build/healthz. Keep `check.sh` the single source of checks.
- Dockerfile: `docker/dockerfiles/Dockerfile.mosaico-dashboard`. Compose: `docker/devel/dashboard-compose.yml` (profiles `development`, `production`).
- Mosaico doesn't accept public PRs (`CONTRIBUTING.md`); upstream ideas start as GitHub Discussions.

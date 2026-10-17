# ADR-0001: The dashboard lives in a self-contained folder of the monorepo

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** (pre-sprint)

## Context

The root `README.md` says the monorepo exists "to simplify the testing and reduce compatibility
issues" between `mosaicod` and `mosaico-sdk-py`. The dashboard depends on both, and the SDK ↔
daemon wire protocol changes between versions (commit `77c0360` moved payloads to protobuf).

## Decision

Build the dashboard as `mosaico-dashboard/` next to `mosaicod/` and `mosaico-sdk-py/`, on the
fork branch `AN/FastAPI_Dashboard`. The folder is self-contained: its own `pyproject.toml`,
`.venv`, Dockerfile, tests and docs. It uses the SDK only through its installed, public API.

## Alternatives considered

- **Separate repository pinned to a PyPI SDK release:** clean separation, but the SDK on `main`
  (`0.8.0-dev`) isn't on PyPI, and a released SDK may not match a daemon built from `main`.
- **Code inside `mosaico-sdk-py/`:** mixes a web app into a library; wrong dependency direction.

## Consequences

- Daemon, SDK and dashboard can be tested together at one commit.
- Only repo-wide config files (`.pre-commit-config.yaml`, `.github/workflows/`) are touched
  outside the folder.
- Extracting to a separate repo later = replace the editable install with a version pin.

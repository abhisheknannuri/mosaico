# ADR-0006: Layered package structure with enforced import rules

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** D-03

## Context

The dashboard has one external system (mosaicod via a blocking SDK), HTML pages for htmx, a
JSON API, and later a background worker that must reuse the same logic. A generic FastAPI layout
(e.g. `api/`, `schemas/`, `models/`, `repositories/`, `core/`, with auth) is designed for
database-backed JSON APIs with users. We have no users, no database yet, and serve HTML.

## Decision

Package `mosaico_dashboard` (src layout, like `mosaicolabs`) with four layers:
`web` (`pages/` HTML, `api/` JSON) → `services` → `gateway` → `domain`. `db/` joins as a sibling
of `gateway` in Sprint 2. Settings and logging stay at the package root (`settings.py`,
`logging_config.py`, matching the SDK's name).

Rules are enforced with `import-linter` contracts in `pyproject.toml`: layer order, only
`gateway` imports `mosaicolabs`, `domain`/`services` don't import FastAPI/Starlette.

Domain models are Pydantic models and may be returned by `web/api` directly. Separate API
schemas are added only when the API shape needs to differ.

Folders are created by the task that first uses them, not in advance.

## Alternatives considered

- **Generic layout (`api/ schemas/ models/ repositories/ core/`):** no place for the
  mosaicod gateway or HTML pages; auth and repositories we don't need yet.
- **Flat modules:** fine today, but routes would end up calling the SDK directly.
- **Hand-written import test:** works, but `import-linter` contracts are declarative and
  readable as documentation.

## Consequences

- Services are reusable from the worker and testable with a fake gateway.
- SDK changes are contained in `gateway/`.
- `bash ./scripts/check.sh` fails on a layer violation (verified with a planted
  `domain → mosaicolabs` import).

# ADR-0003: Single-user dashboard, no accounts

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** (pre-sprint)

## Context

mosaicod has **no users**. It only has API keys (`api_key_t`), which grant global `read` /
`write` / `delete` permissions (`docs/main/docs/daemon/api_key.md`). Multi-user accounts would
be a dashboard-only feature: login, password storage, roles, sessions, CSRF. That's real work
that doesn't show anything about the core problems (data modelling, ingestion, analytics).

## Decision

The dashboard has **no user accounts**. Everyone who can reach it uses it with the same rights.
The Mosaico API keys stay server-side (env vars), with a `read` key for the web process and a
`read|write` key only for the worker (ingestion).

## Alternatives considered

- **Local accounts + roles:** deferred to the icebox.
- **Single shared password:** possible later as a small middleware if a public demo needs it.

## Consequences

- Default bind is `127.0.0.1`. For a shared deployment, put it behind a reverse proxy that does
  authentication (e.g. basic auth, or an OAuth proxy). No code change needed.
- No `users` table, no `created_by` columns.
- If accounts are needed later, add them as a FastAPI dependency (`current_user`) without
  touching services.

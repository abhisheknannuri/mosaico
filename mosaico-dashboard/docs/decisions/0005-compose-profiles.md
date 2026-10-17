# ADR-0005: One compose file with `development` and `production` profiles

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** D-01f

## Context

- `docker/devel/compose.yml` (upstream) is for **Rust development**: it starts only Postgres 16 +
  VersityGW (S3); mosaicod itself runs from `cargo run`. The dashboard doesn't need that.
- `docker/devel/docker-compose2.yml` (local, untracked) runs the **built** daemon
  (`mosaicod:local`) with server, cleanup and store-optimizer, Postgres 18, and filesystem
  storage in `mosaico-data/`. The existing catalog lives in the Docker volume `mosaico_pg-data`.
- We want to (a) develop the dashboard from the Poetry venv with hot reload against a real
  daemon, and (b) regularly test the real container image.

## Decision

New file `docker/devel/dashboard-compose.yml`, derived from `docker-compose2.yml`:
- **`development` profile:** Postgres + mosaicod server/cleanup/store-optimizer. The dashboard
  runs from `.venv` (`uvicorn --reload`) and connects to `localhost:6726`.
- **`production` profile:** the same + `dashboard` container (image from
  `Dockerfile.mosaico-dashboard`). Used to test each finished feature as a container.
- **One** dashboard container: FastAPI serves API, HTML and htmx static files. There's no
  separate frontend server. The worker (Sprint 2) will be a second service from the same image.
- Keep project name `mosaico` and volume `pg-data`, so the existing catalog and the files in
  `mosaico-data/` stay paired. Data path is relative (`../../mosaico-data`) instead of absolute.
- mosaicod has a `build:` section (repo root context), so the daemon can be rebuilt from the same
  commit as the SDK with `--build`; otherwise the existing `mosaicod:local` image is reused.
- Dashboard host port is `${DASHBOARD_PORT:-8000}`, so the container and a dev server don't clash.
- Dashboard sets `NO_PROXY=mosaicod-server,localhost,127.0.0.1`: Docker may inject
  `HTTP(S)_PROXY` from `~/.docker/config.json` and gRPC honours it (seen on this machine:
  connection failed with a proxy 502 until this was set).

## Alternatives considered

- **Extend upstream `compose.yml`:** wrong purpose (no daemon container, S3 gateway we don't need).
- **Two files (dev/prod):** duplicated service definitions that drift.
- **No profiles, dashboard always on:** clashes with the dev server and forces rebuilds.

## Consequences

- Never run `down -v` unless you mean to wipe the catalog. Wiping only the volume would leave
  orphaned files that `mosaicod cleanup` deletes after the retention period.
- Running it alongside upstream `compose.yml` clashes on port 5432; run one at a time.
- `docker/README.md` documents a build context (`../mosaicod`) that no longer matches
  `Dockerfile.mosaicod` (which expects the repo root). Not ours to fix here; noted.

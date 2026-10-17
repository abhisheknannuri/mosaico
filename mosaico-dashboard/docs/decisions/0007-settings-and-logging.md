# ADR-0007: Settings with pydantic-settings, console logging like the SDK

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** D-04

## Context

The SDK (`mosaicolabs/logging_config.py`) logs to the console only (stderr), with standard
`logging`, a plain format by default and an optional Rich "pretty" mode. As a library it only
configures its own `mosaicolabs` logger, and only when `setup_sdk_logging()` is called.
The dashboard is an application: it owns the logging of the whole process (its own code,
uvicorn, the SDK).

## Decision

- **Settings:** one `Settings` class (`pydantic-settings`), `DASHBOARD_` prefix, read from the
  environment and `.env`. Values are validated at startup. The API key is a `SecretStr`.
  `get_settings()` is cached. Only settings that something uses are added.
- **Logging:** console only, root logger, one handler. Plain format identical to the SDK's
  (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`). `DASHBOARD_LOG_FORMAT=plain|pretty`
  (default `plain`) mirrors mosaicod's `MOSAICOD_LOG_FORMAT`; `pretty` uses Rich, like the SDK's
  `pretty=True`. We don't call `setup_sdk_logging()`, so SDK logs propagate
  to our handler. Uvicorn runs with `log_config=None`, so its logs use the same handler.
- **Run command:** `poetry run mosaico-dashboard` (`__main__.run`), also the Docker `CMD`.
  Logging is set up in `run()` (reloader process) and in `main.py` (server process; with
  reload, uvicorn starts the app in a child process).

## Alternatives considered

- **JSON logs in production:** only useful with a log collector; not needed for a local
  dashboard. Can be added later as a third `LOG_FORMAT` value, like mosaicod's `json`.
- **Log files:** need rotation and volumes; `docker logs` and the terminal are enough.
- **`DASHBOARD_ENV` (dev/prod) switch:** nothing depends on it yet.
- **Plain `uvicorn …` command:** works, but host/port/reload would be typed every time instead
  of configured.

## Consequences

- Same log format in the terminal and in `docker logs`.
- Tests that create `Settings()` run in an empty temp directory so a developer's `.env` doesn't
  leak in.

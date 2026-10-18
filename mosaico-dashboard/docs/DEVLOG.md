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
| 2026-10-17 | D-05 | `create_app(settings)`, `/healthz` router with response model, readable operationIds, HTTP conventions in `architecture.md`, ADR-0008. Tests build their own app via a `client` fixture. |
| 2026-10-17 | D-06 | Base template + CSS (dark mode), htmx 2.0.11 vendored, `render()` page-or-fragment helper, home page with htmx Refresh, ADR-0009. Gotcha: `hx-boost` requests also send `HX-Request` but need the full page; `url_for` gave absolute URLs → plain `/static/` paths. |
| 2026-10-17 | D-08 | `dashboard-ci.yml`: `check.sh` on Py 3.10/3.13 (non-editable SDK) + Docker build and `/healthz` smoke test. Simulated locally: 3.10 passes; container runs with the new `CMD`. Waiting for the first GitHub run. |
| 2026-10-17 | D-08 | First GitHub run green. Pre-commit ruff hook verified: it reformats and stops the commit. |
| 2026-10-17 | D-06 | Restyled to match the docs site: Mosaico logo + favicon, brand colours from `docs/py` `extra.css`, gradient nav bar, dark only; simpler HTML/CSS. |
| 2026-10-17 | D-06 | Layout pass: logo 30px in a 64px header with divider + muted label, thinner 40px gradient nav, type scale (15px base), content full width aligned with header, `color-scheme: dark`, card title "Status". Checked with headless Chrome screenshots. |
| 2026-10-18 | D-09 | Domain models (`Recording`, `SensorStream`, `Upload`), `format.py`, `vocabulary.py`, 41 tests. Checked live data first: tags are class names (`IMU`, not `imu`), upload time (2026) ≠ recording time (2024), ROS msgtype available in topic metadata. |
| 2026-10-18 | D-10 | Sync `MosaicoGateway` Protocol + gateway errors, `FakeGateway` with r2b-shaped sample data, 6 tests (47 total). ADR-0012: sync gateway + `def` routes instead of async + threads. |
| 2026-10-18 | D-11 | `SdkGateway`: shared lazy client, caches cleared per call, error translation, mapping; lifespan close; `get_gateway` dependency; unit + integration tests (54). Spike: 40 threads on one client → 0 errors; client survives daemon restart; SDK handler caches never expire (stale data) and `sequence_handler` hides errors as `None`. Gotcha: duplicate test file names → pytest `--import-mode=importlib`. |
| 2026-10-18 | D-11 | Gateways inherit `MosaicoGateway` explicitly (readability); pyright still flags missing methods. |
| 2026-10-18 | D-12 | `check_connection`, `DaemonStatus`, first service `get_daemon_status`, `/readyz` 200/503, header status indicator via htmx every 30 s, connect timeout setting (2 s). Live: started with mosaicod down, indicator recovered on its own. `-rs` shows skip reasons; strict integration flag noted in D-49. |
| 2026-10-18 | D-13 | `make_demo_bags.py` (3 deterministic ROS 2 bags, 6 sensor types, metadata, GPS gap) + `seed_demo.py` (SDK RosbagInjector, skips existing). Verified dry run, ingest, read-back, re-run. Test hygiene: tests no longer read `.env`, logging restored, order-independent; conventions documented. Finding: gaps inside a stream are invisible in start/end times (noted in D-30). |
| 2026-10-18 | D-14 | Recordings list `/recordings` (live): sensor-category chips, newest recorded first, empty state; `RecordingSummary` + recordings service; Jinja filters. Screenshot polish: table edges aligned with heading, tabular numbers, "3 Sep" dates. 0.2 s for 7 recordings (N+1 per recording). |

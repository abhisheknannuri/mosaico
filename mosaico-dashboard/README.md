# Mosaico Dashboard

A web dashboard for the Mosaico Data-Platform. It runs on the machine that has the ROS bags and
talks to mosaicod through the Python SDK; users only need a browser.

- **Overview**: recordings, storage, recorded time and streams per ontology type.
- **Recordings**: every recording with its date, duration, ontology types, streams and size.
- **Ingest**: pick a bag from a folder on this machine, dry run (what will be ingested and what
  is skipped, and why), ingest with live progress, cancel, history. Options: ROS distribution,
  keep partial data, append to an existing recording, topic selection.

Status: prototype. FastAPI with server-rendered HTML (Jinja2 + htmx), Postgres for the
dashboard's own state (ingestion jobs). Architecture: [`docs/architecture.md`](docs/architecture.md).

## 1. Install

Requirements: Poetry 2.5.1+ (`pipx install poetry`), Python 3.10+ (`poetry python install 3.12`),
Docker with Docker Compose.

```bash
git clone https://github.com/abhisheknannuri/mosaico.git
cd mosaico
git checkout AN/FastAPI_Dashboard
cd mosaico-dashboard
bash ./scripts/dev_setup.sh
```

`dev_setup.sh` installs the dashboard into `.venv` and the SDK from `../mosaico-sdk-py` in
editable mode (the dashboard uses two small SDK additions from this branch, see
[SDK changes](#sdk-changes)). `poetry sync` removes the SDK; run `dev_setup.sh` again after it.

## 2. Start mosaicod and the dashboard database

From the repository root:

```bash
docker compose -f docker/devel/dashboard-compose.yml --profile development up -d
```

This starts mosaicod (port 6726) with its Postgres, and `dashboard-db` (Postgres, port 5433).

## 3. Configure

```bash
cp .env.example .env
```

All settings are `DASHBOARD_*` variables in `.env` (or the environment). The defaults work with
the compose setup above; the ones you may want to change:

| Setting | Default | |
| --- | --- | --- |
| `DASHBOARD_INGEST_DIR` | not set | Folder with the ROS bags (absolute path). Can also be chosen on the Ingest page. |
| `DASHBOARD_MOSAICO_HOST` / `_PORT` | `localhost` / `6726` | mosaicod |
| `DASHBOARD_DATABASE_URL` | `dashboard-db` on port 5433 | The dashboard's own database |
| `DASHBOARD_MANAGE_WORKER` | `true` | The web app starts the ingestion worker when needed |

The full list with comments is in [`.env.example`](.env.example).

## 4. Add demo data (optional)

Three small synthetic ROS 2 recordings (IMU, GPS, odometry, camera, battery, temperature):

```bash
poetry run python scripts/seed_demo.py
```

The bags are written to `demo-data/`; set `DASHBOARD_INGEST_DIR` to its absolute path to try
ingesting them again under other names.

## 5. Run

```bash
poetry run mosaico-dashboard
```

Open <http://127.0.0.1:8000>. Database migrations run on start.

Ingestion runs in a separate worker process. The first ingestion starts it; the bar at the top of
the Ingest page shows it, with Start and Stop, and it stops with the web app. It runs one job at
a time; stopping it cancels the running job and keeps the queued ones. To run the worker
yourself, set `DASHBOARD_MANAGE_WORKER=false` and start it in a second terminal:

```bash
poetry run mosaico-dashboard-worker
```

Everything in containers instead (from the repository root):

```bash
docker compose -f docker/devel/dashboard-compose.yml --profile production up -d --build
```

## SDK changes

Two additions in `mosaico-sdk-py` on this branch (see its `CHANGELOG.md`), both backwards
compatible:

- `RosbagInjector.dry_run()` / `MCAPInjector.dry_run()` return a `DryRunReport` (accepted and
  rejected topics with reasons) instead of only printing a table.
- Injector and extractor configs take an optional `progress_callback`, which receives a
  `ProgressSnapshot` (per topic and overall) at most every 0.5 s. The dashboard stores it and
  streams it to the browser.

## Development

```bash
bash ./scripts/check.sh   # format, lint, import rules, types, tests
```

- Tests marked `integration` need mosaicod, tests marked `database` need `dashboard-db`; both are
  skipped when those aren't running.
- After changing `db/tables.py`: `poetry run alembic revision --autogenerate -m "..."`.
- CI (`.github/workflows/dashboard-ci.yml`) runs `check.sh` on Python 3.10 and 3.13 and builds
  the Docker image.
- Design notes: [`docs/architecture.md`](docs/architecture.md), UI rules: [`docs/ui.md`](docs/ui.md).

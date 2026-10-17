# Mosaico Dashboard

Web dashboard for the Mosaico Data-Platform: FastAPI backend, server-rendered HTML with htmx.

## Setting up the dashboard environment

### 1. Get the code

```bash
git clone https://github.com/abhisheknannuri/mosaico.git
cd mosaico/
git checkout AN/FastAPI_Dashboard
cd mosaico-dashboard
```

### 2. Requirements

- Poetry 2.5.1 or higher (Run `pipx install poetry`)
- - Python 3.10 or higher (Run `poetry python install 3.12`)
- Docker with Docker Compose

### 3. Install

```bash
bash ./scripts/dev_setup.sh
```

This installs the dashboard dependencies into `.venv` and the Mosaico SDK from
`../mosaico-sdk-py` in editable mode.

> `poetry sync` removes the SDK (it is not in `poetry.lock`). Run `dev_setup.sh` again after it.

### 4. Start mosaicod

From the repository root:

```bash
docker compose -f docker/devel/dashboard-compose.yml --profile development up -d
```

### 5. Configure

```bash
cp .env.example .env
```

Settings are `DASHBOARD_*` variables, read from the environment or `.env`. The example enables
auto-reload and coloured logs for development.

### 6. Run the dashboard

```bash
poetry run mosaico-dashboard
```

- Health check: <http://127.0.0.1:8000/healthz>
- API docs: <http://127.0.0.1:8000/docs>

## Running everything in containers

From the repository root:

```bash
docker compose -f docker/devel/dashboard-compose.yml --profile production up -d --build
```

## Code standards

Same as `mosaico-sdk-py`: ruff for linting and formatting, plus pyright for type checking and
pytest for tests (config in `pyproject.toml`).

Run all checks:

```bash
bash ./scripts/check.sh
```

Fix formatting and lint issues:

```bash
poetry run ruff format .
poetry run ruff check --fix .
```

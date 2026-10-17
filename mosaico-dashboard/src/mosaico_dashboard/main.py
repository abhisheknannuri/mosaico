"""ASGI entrypoint of the dashboard."""

from fastapi import FastAPI

from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.settings import get_settings

settings = get_settings()
setup_logging(settings.log_level, settings.log_format)

app = FastAPI(title="Mosaico Dashboard")


@app.get("/healthz", tags=["ops"], summary="Process liveness")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

"""ASGI entrypoint of the dashboard."""

from fastapi import FastAPI

app = FastAPI(title="Mosaico Dashboard")


@app.get("/healthz", tags=["ops"], summary="Process liveness")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

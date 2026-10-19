"""Liveness and readiness endpoints for Docker health checks and monitoring."""

from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import Engine

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.status import database_reachable, get_daemon_status
from mosaico_dashboard.web.dependencies import get_engine, get_gateway

router = APIRouter(tags=["ops"])


class Health(BaseModel):
    status: Literal["ok"]


Availability = Literal["ok", "unavailable"]


class Readiness(BaseModel):
    status: Availability
    mosaicod: Availability
    mosaicod_version: str | None
    database: Availability


@router.get("/healthz", summary="Process liveness")
def healthz() -> Health:
    return Health(status="ok")


def _availability(ok: bool) -> Availability:
    return "ok" if ok else "unavailable"


@router.get(
    "/readyz",
    summary="Readiness: mosaicod and the dashboard database are reachable",
    responses={503: {"model": Readiness, "description": "a dependency is unreachable"}},
)
def readyz(
    response: Response,
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
) -> Readiness:
    daemon = get_daemon_status(gateway)
    database_ok = database_reachable(engine)
    ready = daemon.reachable and database_ok
    if not ready:
        response.status_code = 503
    return Readiness(
        status=_availability(ready),
        mosaicod=_availability(daemon.reachable),
        mosaicod_version=daemon.version,
        database=_availability(database_ok),
    )

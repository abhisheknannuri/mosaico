"""Liveness and readiness endpoints for Docker health checks and monitoring."""

from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.status import get_daemon_status
from mosaico_dashboard.web.dependencies import get_gateway

router = APIRouter(tags=["ops"])


class Health(BaseModel):
    status: Literal["ok"]


class Readiness(BaseModel):
    status: Literal["ok", "unavailable"]
    mosaicod_version: str | None


@router.get("/healthz", summary="Process liveness")
def healthz() -> Health:
    return Health(status="ok")


@router.get(
    "/readyz",
    summary="Readiness: mosaicod is reachable",
    responses={503: {"model": Readiness, "description": "mosaicod is unreachable"}},
)
def readyz(
    response: Response, gateway: MosaicoGateway = Depends(get_gateway)
) -> Readiness:
    status = get_daemon_status(gateway)
    if not status.reachable:
        response.status_code = 503
        return Readiness(status="unavailable", mosaicod_version=None)
    return Readiness(status="ok", mosaicod_version=status.version)

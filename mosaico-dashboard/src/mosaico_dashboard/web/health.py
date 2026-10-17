"""Liveness endpoint for Docker health checks and monitoring."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["ops"])


class Health(BaseModel):
    status: Literal["ok"]


@router.get("/healthz", summary="Process liveness")
def healthz() -> Health:
    return Health(status="ok")

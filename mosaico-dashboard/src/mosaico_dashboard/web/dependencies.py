"""FastAPI dependencies shared by routes."""

from fastapi import Request
from sqlalchemy import Engine

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.settings import Settings


def get_gateway(request: Request) -> MosaicoGateway:
    return request.app.state.gateway


def get_engine(request: Request) -> Engine:
    return request.app.state.engine


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings

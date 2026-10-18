"""FastAPI dependencies shared by routes."""

from fastapi import Request

from mosaico_dashboard.gateway.base import MosaicoGateway


def get_gateway(request: Request) -> MosaicoGateway:
    return request.app.state.gateway

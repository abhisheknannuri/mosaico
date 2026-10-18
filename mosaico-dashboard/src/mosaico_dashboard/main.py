"""ASGI entrypoint: builds the FastAPI app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.gateway.sdk import SdkGateway
from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.settings import Settings, get_settings
from mosaico_dashboard.web import health
from mosaico_dashboard.web.pages import home, status

STATIC_DIR = Path(__file__).parent / "web" / "static"


def route_name_as_operation_id(route: APIRoute) -> str:
    return route.name


def sdk_gateway(settings: Settings) -> SdkGateway:
    api_key = settings.mosaico_api_key
    return SdkGateway(
        host=settings.mosaico_host,
        port=settings.mosaico_port,
        api_key=api_key.get_secret_value() if api_key else None,
        tls=settings.mosaico_tls,
        tls_cert_path=settings.mosaico_tls_cert_path,
        connect_timeout=settings.mosaico_connect_timeout,
    )


def create_app(settings: Settings, gateway: MosaicoGateway | None = None) -> FastAPI:
    setup_logging(settings.log_level, settings.log_format)
    gateway = gateway or sdk_gateway(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        gateway.close()

    app = FastAPI(
        title="Mosaico Dashboard",
        version=version("mosaico-dashboard"),
        description="Web dashboard for the Mosaico Data-Platform.",
        generate_unique_id_function=route_name_as_operation_id,
        lifespan=lifespan,
    )
    app.state.gateway = gateway
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(health.router)
    app.include_router(home.router)
    app.include_router(status.router)

    return app


app = create_app(get_settings())

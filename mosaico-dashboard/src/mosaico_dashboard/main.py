"""ASGI entrypoint: builds the FastAPI app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine

from mosaico_dashboard.factories import build_engine, build_gateway
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.settings import Settings, get_settings
from mosaico_dashboard.web import health
from mosaico_dashboard.web.pages import export, ingest, overview, recordings, status

STATIC_DIR = Path(__file__).parent / "web" / "static"


def route_name_as_operation_id(route: APIRoute) -> str:
    return route.name


def create_app(
    settings: Settings,
    gateway: MosaicoGateway | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    setup_logging(settings.log_level, settings.log_format)
    gateway = gateway or build_gateway(settings)
    engine = engine or build_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        gateway.close()
        engine.dispose()

    app = FastAPI(
        title="Mosaico Dashboard",
        version=version("mosaico-dashboard"),
        description="Web dashboard for the Mosaico Data-Platform.",
        generate_unique_id_function=route_name_as_operation_id,
        lifespan=lifespan,
    )
    app.state.gateway = gateway
    app.state.engine = engine
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(health.router)
    app.include_router(overview.router)
    app.include_router(status.router)
    app.include_router(recordings.router)
    app.include_router(ingest.router)
    app.include_router(export.router)

    return app


app = create_app(get_settings())

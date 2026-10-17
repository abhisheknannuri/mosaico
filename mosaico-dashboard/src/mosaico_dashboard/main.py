"""ASGI entrypoint: builds the FastAPI app."""

from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.settings import Settings, get_settings
from mosaico_dashboard.web import health
from mosaico_dashboard.web.pages import home

STATIC_DIR = Path(__file__).parent / "web" / "static"


def route_name_as_operation_id(route: APIRoute) -> str:
    return route.name


def create_app(settings: Settings) -> FastAPI:
    setup_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title="Mosaico Dashboard",
        version=version("mosaico-dashboard"),
        description="Web dashboard for the Mosaico Data-Platform.",
        generate_unique_id_function=route_name_as_operation_id,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(health.router)
    app.include_router(home.router)
    return app


app = create_app(get_settings())

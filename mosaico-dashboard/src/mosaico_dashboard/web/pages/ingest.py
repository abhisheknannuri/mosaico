"""Ingest page: the bags in the ingest folder and the options for the selected one."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Engine

from mosaico_dashboard.domain.models import IngestOptions
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.ingestion import (
    dry_run_ingestion,
    find_bag_file,
    get_ingest_folder,
    list_ingestions,
    start_ingestion,
)
from mosaico_dashboard.settings import Settings
from mosaico_dashboard.web.dependencies import (
    get_app_settings,
    get_engine,
    get_gateway,
)
from mosaico_dashboard.web.rendering import render, templates

router = APIRouter(include_in_schema=False)


def form_options(
    ros_distro: str,
    keep_partial: bool,
    update_if_exists: bool,
    topics: list[str],
    topics_chosen: bool,
) -> IngestOptions:
    """`topics` is used only when the form had the topic checkboxes (after a dry run)."""
    return IngestOptions(
        ros_distro=ros_distro or None,
        keep_partial=keep_partial,
        update_if_exists=update_if_exists,
        topics=topics if topics_chosen else None,
    )


@router.get("/ingest", response_class=HTMLResponse)
def ingest(
    request: Request,
    file: str | None = None,
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir, engine)
    context = {
        "folder": folder,
        "selected": find_bag_file(folder, file),
        "history": list_ingestions(engine),
        "ros_distros": gateway.ros_distros(),
        "defaults": settings,
    }
    return render(request, "pages/ingest.html", "partials/ingest.html", context)


@router.post("/ingest/dry-run", response_class=HTMLResponse)
def dry_run(
    request: Request,
    file: str = Form(),
    sequence_name: str = Form(""),
    metadata_key: list[str] = Form(default=[]),
    metadata_value: list[str] = Form(default=[]),
    ros_distro: str = Form(""),
    keep_partial: bool = Form(False),
    update_if_exists: bool = Form(False),
    topic: list[str] = Form(default=[]),
    topics_chosen: bool = Form(False),
    gateway: MosaicoGateway = Depends(get_gateway),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir)
    selected = find_bag_file(folder, file)
    if selected is None:
        context = {"error": f"'{file}' is not in the ingest folder anymore."}
        return templates.TemplateResponse(
            request, "partials/ingest_dry_run.html", context
        )
    options = form_options(
        ros_distro, keep_partial, update_if_exists, topic, topics_chosen
    )
    result = dry_run_ingestion(
        gateway, selected, sequence_name, metadata_key, metadata_value, options
    )
    context = {"result": result, "error": result.error}
    return templates.TemplateResponse(request, "partials/ingest_dry_run.html", context)


@router.post("/ingest/start", response_class=HTMLResponse)
def start(
    request: Request,
    file: str = Form(),
    sequence_name: str = Form(""),
    metadata_key: list[str] = Form(default=[]),
    metadata_value: list[str] = Form(default=[]),
    skipped_confirmed: bool = Form(False),
    ros_distro: str = Form(""),
    keep_partial: bool = Form(False),
    update_if_exists: bool = Form(False),
    topic: list[str] = Form(default=[]),
    topics_chosen: bool = Form(False),
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir)
    selected = find_bag_file(folder, file)
    if selected is None:
        context = {"error": f"'{file}' is not in the ingest folder anymore."}
        return templates.TemplateResponse(
            request, "partials/ingest_dry_run.html", context
        )
    result, job = start_ingestion(
        gateway,
        engine,
        selected,
        sequence_name,
        metadata_key,
        metadata_value,
        skipped_confirmed,
        form_options(ros_distro, keep_partial, update_if_exists, topic, topics_chosen),
    )
    if job is None:
        context = {
            "result": result,
            "error": result.error,
            "confirm_needed": result.verdict == "warn",
        }
        return templates.TemplateResponse(
            request, "partials/ingest_dry_run.html", context
        )
    return HTMLResponse("", headers={"HX-Redirect": f"/ingest/jobs/{job.id}"})

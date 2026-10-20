"""Ingest page: the bags in the ingest folder and the options for the selected one."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Engine

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.ingestion import (
    dry_run_ingestion,
    find_bag_file,
    get_ingest_folder,
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


@router.get("/ingest", response_class=HTMLResponse)
def ingest(
    request: Request,
    file: str | None = None,
    gateway: MosaicoGateway = Depends(get_gateway),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir)
    context = {"folder": folder, "selected": find_bag_file(folder, file)}
    return render(request, "pages/ingest.html", "partials/ingest.html", context)


@router.post("/ingest/dry-run", response_class=HTMLResponse)
def dry_run(
    request: Request,
    file: str = Form(),
    sequence_name: str = Form(""),
    metadata_key: list[str] = Form(default=[]),
    metadata_value: list[str] = Form(default=[]),
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
    result = dry_run_ingestion(
        gateway, selected, sequence_name, metadata_key, metadata_value
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

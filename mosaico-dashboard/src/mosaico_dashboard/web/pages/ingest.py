"""Ingest page: tabs Manual ingest, Watchdog and History; the right panel and the activity bar."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from mosaico_dashboard.domain.models import IngestOptions
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.ingestion import (
    dry_run_ingestion,
    find_bag_file,
    get_active_ingestion,
    get_ingest_folder,
    get_ingestion,
    list_ingestions,
    start_ingestion,
)
from mosaico_dashboard.services.processes import ProcessManager
from mosaico_dashboard.services.worker import (
    WORKER_NAME,
    ensure_worker,
    stop_worker,
    worker_status,
)
from mosaico_dashboard.settings import Settings
from mosaico_dashboard.web.dependencies import (
    get_app_settings,
    get_engine,
    get_gateway,
    get_processes,
)
from mosaico_dashboard.web.pages.ingest_jobs import job_context
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


def activity_context(request: Request, engine: Engine) -> dict:
    settings: Settings = request.app.state.settings
    processes: ProcessManager = request.app.state.processes
    status = worker_status(engine)
    try:
        job = get_active_ingestion(engine) if status else None
    except SQLAlchemyError:
        job = None
    return {
        "worker": status,
        "worker_starting": processes.is_alive(WORKER_NAME),
        "manage_worker": settings.manage_worker,
        "active_job": job,
    }


def detail_context(
    gateway: MosaicoGateway,
    engine: Engine,
    settings: Settings,
    folder,
    file: str | None,
    job_id: str | None,
) -> dict:
    job = get_ingestion(engine, job_id) if job_id else None
    context: dict = {
        "selected": find_bag_file(folder, file),
        "ros_distros": gateway.ros_distros(),
        "defaults": settings,
        "detail_job": job,
    }
    if job is not None:
        context |= job_context(job)
    return context


def page(request: Request, tab: str, context: dict, engine: Engine) -> HTMLResponse:
    context |= {"tab": tab, "tab_template": f"partials/ingest_{tab}.html"}
    context |= activity_context(request, engine)
    return render(request, "pages/ingest.html", f"partials/ingest_{tab}.html", context)


@router.get("/ingest", response_class=HTMLResponse)
def manual(
    request: Request,
    file: str | None = None,
    job: str | None = None,
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir, engine)
    context = {"folder": folder} | detail_context(
        gateway, engine, settings, folder, file, job
    )
    return page(request, "manual", context, engine)


@router.get("/ingest/watchdog", response_class=HTMLResponse)
def watchdog(
    request: Request,
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir, engine)
    return page(request, "watchdog", {"folder": folder, "selected": None}, engine)


@router.get("/ingest/history", response_class=HTMLResponse)
def history(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    return page(request, "history", {"history": list_ingestions(engine)}, engine)


@router.get("/ingest/detail", response_class=HTMLResponse)
def detail(
    request: Request,
    file: str | None = None,
    job: str | None = None,
    gateway: MosaicoGateway = Depends(get_gateway),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> HTMLResponse:
    folder = get_ingest_folder(gateway, settings.ingest_dir, engine)
    context = detail_context(gateway, engine, settings, folder, file, job)
    return templates.TemplateResponse(request, "partials/ingest_detail.html", context)


@router.get("/ingest/activity", response_class=HTMLResponse)
def activity(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/ingest_activity.html", activity_context(request, engine)
    )


@router.post("/ingest/worker/start", response_class=HTMLResponse)
def worker_start(
    request: Request,
    engine: Engine = Depends(get_engine),
    processes: ProcessManager = Depends(get_processes),
) -> HTMLResponse:
    ensure_worker(engine, processes)
    return activity(request, engine)


@router.post("/ingest/worker/stop", response_class=HTMLResponse)
def worker_stop(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    stop_worker(engine)
    return activity(request, engine)


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
    processes: ProcessManager = Depends(get_processes),
) -> HTMLResponse:
    """Queues the job (starting the worker if needed) and shows it in the right panel;
    otherwise shows why not."""
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
    if settings.manage_worker:
        ensure_worker(engine, processes)
    context = {"detail_job": job, "selected": selected} | job_context(job)
    response = templates.TemplateResponse(
        request, "partials/ingest_detail.html", context
    )
    response.headers["HX-Retarget"] = "#ingest-detail"
    response.headers["HX-Reswap"] = "innerHTML"
    response.headers["HX-Push-Url"] = f"/ingest?job={job.id}"
    return response

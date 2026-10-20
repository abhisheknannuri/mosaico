"""One ingestion job: its page, live progress (SSE), cancel; the top-bar indicator."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from mosaico_dashboard.domain.models import Job
from mosaico_dashboard.services.ingestion import (
    cancel_job,
    error_hint,
    get_active_ingestion,
    get_ingestion,
)
from mosaico_dashboard.web.dependencies import get_engine
from mosaico_dashboard.web.rendering import templates

router = APIRouter(include_in_schema=False)

EVENT_INTERVAL_SECONDS = 0.5
WAITING_HINT_SECONDS = 5


def job_context(job: Job) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "job": job,
        "hint": error_hint(job.error),
        "elapsed": (job.finished_at or now) - job.started_at
        if job.started_at
        else None,
        "waiting": job.status == "queued"
        and (now - job.created_at).total_seconds() > WAITING_HINT_SECONDS,
    }


def progress_html(job: Job) -> str:
    template = templates.get_template("partials/ingest_job_progress.html")
    return template.render(job_context(job))


def sse_event(event: str, data: str) -> str:
    lines = "".join(f"data: {line}\n" for line in data.splitlines() or [""])
    return f"event: {event}\n{lines}\n"


@router.get("/ingest/jobs/{job_id}")
def job_page(job_id: str, engine: Engine = Depends(get_engine)) -> RedirectResponse:
    """Jobs are shown in the Ingest page's right panel."""
    if get_ingestion(engine, job_id) is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return RedirectResponse(f"/ingest?job={job_id}", status_code=303)


@router.post("/ingest/jobs/{job_id}/cancel", response_class=HTMLResponse)
def cancel(job_id: str, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    job = cancel_job(engine, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return HTMLResponse(progress_html(job))


@router.get("/ingest/jobs/{job_id}/events")
async def job_events(
    job_id: str, request: Request, engine: Engine = Depends(get_engine)
) -> StreamingResponse:
    """Server-sent events: `progress` with the progress HTML when it changes, `done` once the
    job has finished."""

    async def events() -> AsyncIterator[str]:
        last = None
        while not await request.is_disconnected():
            job = await run_in_threadpool(get_ingestion, engine, job_id)
            if job is None:
                yield sse_event("done", "")
                return
            html = progress_html(job)
            if html != last:
                yield sse_event("progress", html)
                last = html
            if job.finished:
                yield sse_event("done", "")
                return
            await asyncio.sleep(EVENT_INTERVAL_SECONDS)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/ingest/active", response_class=HTMLResponse)
def active(request: Request, engine: Engine = Depends(get_engine)) -> HTMLResponse:
    try:
        job = get_active_ingestion(engine)
    except SQLAlchemyError:
        job = None
    return templates.TemplateResponse(
        request, "partials/ingest_active.html", {"job": job}
    )

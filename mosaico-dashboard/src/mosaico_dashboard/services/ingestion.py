"""Ingestion: the bags in the ingest folder, and jobs that ingest them in the worker."""

from pathlib import Path

from sqlalchemy import Engine

from mosaico_dashboard.db.jobs import (
    enqueue,
    finish,
    get_job,
    request_cancel,
    save_progress,
)
from mosaico_dashboard.domain.models import (
    BagFile,
    IngestFolder,
    IngestRequest,
    Job,
    JobStatus,
    Progress,
)
from mosaico_dashboard.gateway.base import GatewayUnavailable, MosaicoGateway

INGEST_JOB = "ingest"


def get_ingest_folder(gateway: MosaicoGateway, folder: Path | None) -> IngestFolder:
    """The bags in the ingest folder, each marked when a recording with its name exists."""
    if folder is None:
        return IngestFolder(path=None, status="not_configured", files=[])
    try:
        files = gateway.list_bag_files(folder)
    except ValueError:
        return IngestFolder(path=str(folder), status="missing", files=[])
    try:
        names = {r.name for r in gateway.list_recordings()}
    except GatewayUnavailable:
        return IngestFolder(path=str(folder), status="ok", files=files)
    return IngestFolder(
        path=str(folder),
        status="ok",
        files=[
            f.model_copy(update={"in_mosaico": f.recording_name in names})
            for f in files
        ],
    )


def find_bag_file(folder: IngestFolder, relative_path: str | None) -> BagFile | None:
    """Only files from the listing can be selected."""
    return next((f for f in folder.files if f.relative_path == relative_path), None)


def enqueue_ingestion(engine: Engine, request: IngestRequest) -> Job:
    with engine.begin() as connection:
        return enqueue(connection, INGEST_JOB, request.model_dump())


def cancel_job(engine: Engine, job_id: str) -> Job | None:
    with engine.begin() as connection:
        request_cancel(connection, job_id)
        return get_job(connection, job_id)


def run_job(gateway: MosaicoGateway, engine: Engine, job_id: str) -> None:
    """Runs a claimed job and records its progress and outcome on the job row."""
    with engine.begin() as connection:
        job = get_job(connection, job_id)
    if job is None:
        return
    if job.kind != INGEST_JOB:
        _finish(engine, job_id, "failed", f"Unknown job kind '{job.kind}'")
        return

    def report(progress: Progress) -> None:
        with engine.begin() as connection:
            save_progress(connection, job_id, progress)

    try:
        outcome = gateway.ingest(IngestRequest.model_validate(job.params), report)
    except KeyboardInterrupt:
        outcome = "cancelled"
    except Exception as error:
        _finish(engine, job_id, "failed", str(error) or type(error).__name__)
        return
    _finish(engine, job_id, outcome)


def _finish(
    engine: Engine, job_id: str, status: JobStatus, error: str | None = None
) -> None:
    with engine.begin() as connection:
        finish(connection, job_id, status, error)

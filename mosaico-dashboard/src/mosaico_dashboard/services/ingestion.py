"""Ingestion: the bags in the ingest folder, and jobs that ingest them in the worker."""

from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from mosaico_dashboard.db.jobs import (
    active_job,
    enqueue,
    finish,
    get_job,
    list_jobs,
    request_cancel,
    save_progress,
)
from mosaico_dashboard.domain.models import (
    BagFile,
    DryRun,
    DryRunTopic,
    IngestFolder,
    IngestOptions,
    IngestRequest,
    Job,
    JobStatus,
    Progress,
    recording_name_problem,
)
from mosaico_dashboard.gateway.base import (
    GatewayUnavailable,
    MosaicoGateway,
    RecordingNotFound,
)

INGEST_JOB = "ingest"


def get_ingest_folder(
    gateway: MosaicoGateway, folder: Path | None, engine: Engine | None = None
) -> IngestFolder:
    """The bags in the ingest folder, each marked when a recording with its name exists,
    and as partial when its latest ingestion failed or was cancelled with data kept."""
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
    partial = _partially_ingested(engine) if engine is not None else set()
    return IngestFolder(
        path=str(folder),
        status="ok",
        files=[
            f.model_copy(
                update={
                    "in_mosaico": f.recording_name in names,
                    "partial": f.recording_name in names
                    and f.recording_name in partial,
                }
            )
            for f in files
        ],
    )


def _partially_ingested(engine: Engine) -> set[str]:
    """Recording names whose latest ingestion ended without completing, with data kept."""
    jobs = list_ingestions(engine, limit=500) or []
    latest: dict[str, Job] = {}
    for job in jobs:
        latest.setdefault(job.params["sequence_name"], job)
    return {
        name
        for name, job in latest.items()
        if job.status in ("failed", "cancelled") and job.params.get("keep_partial")
    }


def metadata_from_rows(keys: list[str], values: list[str]) -> dict[str, str]:
    """Key/value rows of the form; rows without a key are ignored.

    Raises ValueError when a key is used twice.
    """
    metadata: dict[str, str] = {}
    for key, value in zip(keys, values):
        key = key.strip()
        if not key:
            continue
        if key in metadata:
            raise ValueError(f"The metadata key '{key}' is used twice.")
        metadata[key] = value.strip()
    return metadata


def dry_run_ingestion(
    gateway: MosaicoGateway,
    file: BagFile,
    sequence_name: str,
    metadata_keys: list[str],
    metadata_values: list[str],
    options: IngestOptions | None = None,
) -> DryRun:
    """Checks the form and asks the SDK what ingesting the bag would do."""
    options = options or IngestOptions()
    sequence_name = sequence_name.strip()
    problem = recording_name_problem(sequence_name)
    if problem:
        return DryRun(request=None, error=problem)
    try:
        metadata = metadata_from_rows(metadata_keys, metadata_values)
    except ValueError as error:
        return DryRun(request=None, error=str(error))
    if options.ros_distro and options.ros_distro not in gateway.ros_distros():
        return DryRun(
            request=None, error=f"Unknown ROS distribution '{options.ros_distro}'."
        )
    if options.topics == []:
        return DryRun(request=None, error="Select at least one topic to ingest.")
    request = IngestRequest(
        file_path=file.path,
        sequence_name=sequence_name,
        metadata=metadata,
        **options.model_dump(),
    )
    try:
        topics = gateway.dry_run(request)
    except Exception as error:
        return DryRun(request=request, error=str(error) or type(error).__name__)
    if request.update_if_exists:
        try:
            return _without_existing_topics(gateway, request, topics)
        except GatewayUnavailable as error:
            return DryRun(
                request=request,
                error=f"mosaicod is not reachable, so the existing recording can't be checked: {error}",
            )
    return DryRun(request=request, topics=topics)


ALREADY_IN_RECORDING = "Already in the recording"


def _without_existing_topics(
    gateway: MosaicoGateway, request: IngestRequest, topics: list[DryRunTopic]
) -> DryRun:
    """When appending, topics the recording already has are skipped and left out of the
    SDK's topic filter."""
    try:
        existing = {s.topic for s in gateway.list_streams(request.sequence_name)}
    except RecordingNotFound:
        return DryRun(request=request, topics=topics)
    clashing = {t.name for t in topics if t.accepted and t.name in existing}
    if not clashing:
        return DryRun(request=request, topics=topics)
    wanted = request.topics if request.topics is not None else [t.name for t in topics]
    filtered = request.model_copy(
        update={"topics": [name for name in wanted if name not in clashing]}
    )
    marked = [
        DryRunTopic(name=t.name, accepted=False, reason=ALREADY_IN_RECORDING)
        if t.name in clashing
        else t
        for t in topics
    ]
    return DryRun(request=filtered, topics=marked)


def start_ingestion(
    gateway: MosaicoGateway,
    engine: Engine,
    file: BagFile,
    sequence_name: str,
    metadata_keys: list[str],
    metadata_values: list[str],
    skipped_confirmed: bool,
    options: IngestOptions | None = None,
) -> tuple[DryRun, Job | None]:
    """Checks the form and dry-runs again; queues the job when nothing blocks and skipped
    topics, if any, were confirmed. Returns the dry run and the job (None if not queued)."""
    result = dry_run_ingestion(
        gateway, file, sequence_name, metadata_keys, metadata_values, options
    )
    if result.request is None or result.verdict == "blocked":
        return result, None
    if result.verdict == "warn" and not skipped_confirmed:
        return result, None
    return result, enqueue_ingestion(engine, result.request)


def get_ingestion(engine: Engine, job_id: str) -> Job | None:
    with engine.connect() as connection:
        return get_job(connection, job_id)


HISTORY_LENGTH = 20


def list_ingestions(engine: Engine, limit: int = HISTORY_LENGTH) -> list[Job] | None:
    """Recent ingestions, newest first; None when the dashboard database is unreachable."""
    try:
        with engine.connect() as connection:
            return list_jobs(connection, INGEST_JOB, limit)
    except SQLAlchemyError:
        return None


def get_active_ingestion(engine: Engine) -> Job | None:
    with engine.connect() as connection:
        return active_job(connection)


_HINTS = [
    (
        ("already exists",),
        "A recording with this name already exists in Mosaico. Choose another name, or "
        'tick "Append to the existing recording" in the advanced options.',
    ),
    (
        ("unavailable", "failed to connect", "connection refused"),
        "mosaicod could not be reached. Check that it is running "
        "(compose profile development) and try again.",
    ),
    (
        ("unauthenticated", "unauthorized", "permission"),
        "mosaicod refused the upload. The API key (DASHBOARD_MOSAICO_API_KEY) needs the "
        "write permission.",
    ),
]


def error_hint(error: str | None) -> str | None:
    """A suggestion for errors the user can fix; None for others."""
    text = (error or "").lower()
    for words, hint in _HINTS:
        if any(word in text for word in words):
            return hint
    return None


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

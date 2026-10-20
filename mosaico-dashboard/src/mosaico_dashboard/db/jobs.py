"""Repository: the job queue (one table, claimed with SKIP LOCKED on Postgres)."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Connection, RowMapping, select, update

from mosaico_dashboard.db.common import utc
from mosaico_dashboard.db.tables import job
from mosaico_dashboard.domain.models import Job, JobStatus, Progress

INTERRUPTED_ERROR = "Interrupted: the worker stopped while this job was running."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_job(row: RowMapping) -> Job:
    return Job(
        id=row["id"],
        kind=row["kind"],
        status=row["status"],
        params=row["params"],
        progress=row["progress"],
        error=row["error"],
        cancel_requested=row["cancel_requested"],
        created_at=utc(row["created_at"]),
        started_at=utc(row["started_at"]),
        finished_at=utc(row["finished_at"]),
    )


def enqueue(connection: Connection, kind: str, params: dict[str, Any]) -> Job:
    job_id = str(uuid.uuid4())
    connection.execute(
        job.insert().values(
            id=job_id,
            kind=kind,
            status="queued",
            params=params,
            cancel_requested=False,
            created_at=_now(),
        )
    )
    found = get_job(connection, job_id)
    assert found is not None
    return found


def get_job(connection: Connection, job_id: str) -> Job | None:
    row = connection.execute(select(job).where(job.c.id == job_id)).mappings().first()
    return _to_job(row) if row else None


def list_jobs(connection: Connection, limit: int = 50) -> list[Job]:
    """Newest first."""
    rows = connection.execute(
        select(job).order_by(job.c.created_at.desc()).limit(limit)
    ).mappings()
    return [_to_job(row) for row in rows]


def claim_next(connection: Connection) -> Job | None:
    """Oldest queued job, marked running; concurrent workers skip each other's rows."""
    row = connection.execute(
        select(job.c.id)
        .where(job.c.status == "queued")
        .order_by(job.c.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if row is None:
        return None
    connection.execute(
        update(job)
        .where(job.c.id == row.id)
        .values(status="running", started_at=_now())
    )
    return get_job(connection, row.id)


def save_progress(connection: Connection, job_id: str, progress: Progress) -> None:
    connection.execute(
        update(job).where(job.c.id == job_id).values(progress=progress.model_dump())
    )


def finish(
    connection: Connection, job_id: str, status: JobStatus, error: str | None = None
) -> None:
    connection.execute(
        update(job)
        .where(job.c.id == job_id)
        .values(status=status, error=error, finished_at=_now())
    )


def request_cancel(connection: Connection, job_id: str) -> None:
    """A queued job is cancelled at once; a running one is flagged for the worker."""
    connection.execute(
        update(job)
        .where(job.c.id == job_id, job.c.status == "queued")
        .values(status="cancelled", finished_at=_now())
    )
    connection.execute(
        update(job)
        .where(job.c.id == job_id, job.c.status == "running")
        .values(cancel_requested=True)
    )


def fail_interrupted(connection: Connection) -> int:
    """Marks jobs left running by a stopped worker as failed. Returns how many."""
    result = connection.execute(
        update(job)
        .where(job.c.status == "running")
        .values(status="failed", error=INTERRUPTED_ERROR, finished_at=_now())
    )
    return result.rowcount

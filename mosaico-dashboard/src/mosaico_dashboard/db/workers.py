"""Repository: the worker's heartbeat and stop request (one row, name "ingest")."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import Connection, Engine, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from mosaico_dashboard.db.common import utc
from mosaico_dashboard.db.tables import worker
from mosaico_dashboard.domain.models import WorkerStatus

WORKER_NAME = "worker"
HEARTBEAT_TIMEOUT = timedelta(seconds=10)
WORKER_LOCK_ID = 7_202_611


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _upsert(connection: Connection, **values) -> None:
    insert = pg_insert if connection.dialect.name == "postgresql" else sqlite_insert
    statement = insert(worker).values(name=WORKER_NAME, **values)
    connection.execute(
        statement.on_conflict_do_update(index_elements=["name"], set_=values)
    )


def register_worker(connection: Connection, pid: int) -> None:
    now = _now()
    _upsert(connection, pid=pid, started_at=now, heartbeat_at=now, stop_requested=False)


def heartbeat(connection: Connection) -> bool:
    """Records that the worker is alive; returns True when a stop was requested."""
    connection.execute(
        update(worker).where(worker.c.name == WORKER_NAME).values(heartbeat_at=_now())
    )
    return bool(
        connection.execute(
            select(worker.c.stop_requested).where(worker.c.name == WORKER_NAME)
        ).scalar()
    )


def unregister_worker(connection: Connection) -> None:
    _upsert(connection, pid=None, heartbeat_at=None, stop_requested=False)


def request_worker_stop(connection: Connection) -> None:
    connection.execute(
        update(worker).where(worker.c.name == WORKER_NAME).values(stop_requested=True)
    )


def get_worker_status(connection: Connection) -> WorkerStatus:
    row = (
        connection.execute(select(worker).where(worker.c.name == WORKER_NAME))
        .mappings()
        .first()
    )
    if row is None:
        return WorkerStatus(running=False)
    heartbeat_at = utc(row["heartbeat_at"])
    alive = heartbeat_at is not None and _now() - heartbeat_at < HEARTBEAT_TIMEOUT
    return WorkerStatus(
        running=alive,
        pid=row["pid"] if alive else None,
        started_at=utc(row["started_at"]) if alive else None,
        heartbeat_at=heartbeat_at,
        stop_requested=row["stop_requested"],
    )


def take_worker_lock(engine: Engine) -> Connection | None:
    """A connection holding the single-worker lock (Postgres), or None if another worker
    holds it. On other databases there is no lock: returns an open connection."""
    connection = engine.connect()
    if connection.dialect.name != "postgresql":
        return connection
    if connection.execute(
        text(f"SELECT pg_try_advisory_lock({WORKER_LOCK_ID})")
    ).scalar():
        return connection
    connection.close()
    return None


def release_worker_lock(connection: Connection) -> None:
    """Releases the lock taken by `take_worker_lock` and closes the connection."""
    if connection.dialect.name == "postgresql":
        connection.execute(text(f"SELECT pg_advisory_unlock({WORKER_LOCK_ID})"))
    connection.close()

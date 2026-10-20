"""The background worker: status from its heartbeat, start on demand, stop request."""

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from mosaico_dashboard.db.workers import (
    WORKER_NAME,
    get_worker_status,
    request_worker_stop,
)
from mosaico_dashboard.domain.models import WorkerStatus
from mosaico_dashboard.services.processes import ProcessManager


def worker_status(engine: Engine) -> WorkerStatus | None:
    """None when the dashboard database is unreachable."""
    try:
        with engine.connect() as connection:
            return get_worker_status(connection)
    except SQLAlchemyError:
        return None


def ensure_worker(engine: Engine, processes: ProcessManager) -> bool:
    """Starts the worker when no running one reports a heartbeat. True if started."""
    status = worker_status(engine)
    if status is not None and status.running:
        return False
    processes.start(WORKER_NAME)
    return True


def stop_worker(engine: Engine) -> None:
    with engine.begin() as connection:
        request_worker_stop(connection)

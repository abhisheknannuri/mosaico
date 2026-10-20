import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, update

from mosaico_dashboard.db.jobs import enqueue, get_job
from mosaico_dashboard.db.tables import worker
from mosaico_dashboard.db.workers import (
    get_worker_status,
    heartbeat,
    register_worker,
    request_worker_stop,
    unregister_worker,
)
from mosaico_dashboard.jobs.worker import Worker
from mosaico_dashboard.services.processes import ProcessManager
from mosaico_dashboard.services.worker import ensure_worker, stop_worker, worker_status


def test_no_worker_yet(sqlite_engine):
    with sqlite_engine.begin() as c:
        assert get_worker_status(c).running is False


def test_registered_worker_is_running_until_its_heartbeat_is_old(sqlite_engine):
    with sqlite_engine.begin() as c:
        register_worker(c, 4242)
        status = get_worker_status(c)
        assert (status.running, status.pid) == (True, 4242)
        old = datetime.now(timezone.utc) - timedelta(seconds=60)
        c.execute(update(worker).values(heartbeat_at=old))
        assert get_worker_status(c).running is False


def test_stop_request_is_reported_by_the_heartbeat(sqlite_engine):
    with sqlite_engine.begin() as c:
        register_worker(c, 1)
        assert heartbeat(c) is False
        request_worker_stop(c)
        assert heartbeat(c) is True
        unregister_worker(c)
        assert get_worker_status(c).running is False
        register_worker(c, 2)
        assert heartbeat(c) is False


def test_ensure_worker_starts_only_when_none_is_running(sqlite_engine, fake_processes):
    processes = fake_processes

    assert ensure_worker(sqlite_engine, processes) is True  # type: ignore[arg-type]
    with sqlite_engine.begin() as c:
        register_worker(c, 1)
    assert ensure_worker(sqlite_engine, processes) is False  # type: ignore[arg-type]
    assert processes.started == ["worker"]


def test_worker_status_when_the_database_is_down():
    engine = create_engine("postgresql+psycopg://x:x@127.0.0.1:1/x")

    assert worker_status(engine) is None


@pytest.fixture
def file_engine(sqlite_file):
    engine = create_engine(f"sqlite:///{sqlite_file}")
    yield engine
    engine.dispose()


def test_worker_registers_and_stops_on_request(file_engine):
    worker_loop = Worker(
        file_engine,
        poll_seconds=0.1,
        command=lambda job_id: [sys.executable, "-c", "pass"],
    )
    thread = threading.Thread(target=worker_loop.run)
    thread.start()
    time.sleep(0.5)
    status = worker_status(file_engine)
    assert status is not None and status.running

    stop_worker(file_engine)
    thread.join(timeout=10)

    assert not thread.is_alive()
    status = worker_status(file_engine)
    assert status is not None and status.running is False


def test_stop_request_cancels_the_running_job(file_engine):
    with file_engine.begin() as c:
        job_id = enqueue(c, "ingest", {}).id
    worker_loop = Worker(
        file_engine,
        poll_seconds=0.1,
        command=lambda job_id: [sys.executable, "-c", "import time\ntime.sleep(30)"],
    )
    thread = threading.Thread(target=worker_loop.run)
    thread.start()
    time.sleep(1)

    stop_worker(file_engine)
    thread.join(timeout=15)

    assert not thread.is_alive()
    with file_engine.begin() as c:
        job = get_job(c, job_id)
    assert job is not None and job.status == "cancelled"


def test_process_manager_starts_each_name_once_and_stops_all():
    sleep = [sys.executable, "-c", "import time\ntime.sleep(30)"]
    processes = ProcessManager({"worker": sleep, "watchdog": sleep})
    assert processes.is_alive("worker") is False

    processes.start("worker")
    processes.start("worker")
    processes.start("watchdog")
    assert processes.is_alive("worker") and processes.is_alive("watchdog")

    processes.stop_all()
    assert not processes.is_alive("worker") and not processes.is_alive("watchdog")

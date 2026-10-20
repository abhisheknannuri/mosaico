import sys
import threading
import time

import pytest
from sqlalchemy import create_engine

from mosaico_dashboard.db.jobs import INTERRUPTED_ERROR, claim_next, enqueue, get_job
from mosaico_dashboard.jobs.worker import Worker
from mosaico_dashboard.services.ingestion import cancel_job


@pytest.fixture
def engine(sqlite_file):
    engine = create_engine(f"sqlite:///{sqlite_file}")
    yield engine
    engine.dispose()


def python(code: str):
    """A child command running `code`, with the job id in `job_id`."""
    return lambda job_id: [sys.executable, "-c", f"job_id = {job_id!r}\n{code}"]


def mark_completed(sqlite_file) -> str:
    return (
        "import sqlite3\n"
        f"c = sqlite3.connect({str(sqlite_file)!r})\n"
        "c.execute(\"UPDATE job SET status = 'completed' WHERE id = ?\", (job_id,))\n"
        "c.commit()\n"
    )


def queued(engine) -> str:
    with engine.begin() as c:
        return enqueue(c, "ingest", {}).id


def status(engine, job_id):
    with engine.begin() as c:
        job = get_job(c, job_id)
    assert job is not None
    return job


def test_empty_queue(engine):
    assert Worker(engine, command=python("pass")).run_once() is False


def test_the_child_records_the_outcome(engine, sqlite_file):
    job_id = queued(engine)

    assert Worker(engine, command=python(mark_completed(sqlite_file))).run_once()

    assert status(engine, job_id).status == "completed"


def test_a_child_that_dies_fails_the_job(engine):
    job_id = queued(engine)

    Worker(engine, command=python("raise SystemExit(3)")).run_once()

    job = status(engine, job_id)
    assert job.status == "failed"
    assert job.error is not None and "exit code 3" in job.error


def test_cancel_sends_ctrl_c_to_the_child(engine):
    job_id = queued(engine)
    worker = Worker(engine, command=python("import time\ntime.sleep(30)"))
    thread = threading.Thread(target=worker.run_once)
    thread.start()
    time.sleep(1)

    cancel_job(engine, job_id)
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert status(engine, job_id).status == "cancelled"


def test_stopping_the_worker_cancels_the_running_job(engine):
    job_id = queued(engine)
    worker = Worker(engine, command=python("import time\ntime.sleep(30)"))
    thread = threading.Thread(target=worker.run)
    thread.start()
    time.sleep(1)

    worker.stop()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert status(engine, job_id).status == "cancelled"


def test_start_fails_jobs_left_running(engine):
    job_id = queued(engine)
    with engine.begin() as c:
        claim_next(c)
    worker = Worker(engine, command=python("pass"))
    worker.stop()

    worker.run()

    job = status(engine, job_id)
    assert (job.status, job.error) == ("failed", INTERRUPTED_ERROR)

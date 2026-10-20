from mosaico_dashboard.db.jobs import (
    INTERRUPTED_ERROR,
    claim_next,
    enqueue,
    fail_interrupted,
    finish,
    get_job,
    list_jobs,
    request_cancel,
    save_progress,
)
from mosaico_dashboard.domain.models import Progress, TopicProgress


def test_enqueue_and_get(sqlite_engine):
    with sqlite_engine.begin() as c:
        job = enqueue(c, "ingest", {"file_path": "/bags/a.mcap"})
        found = get_job(c, job.id)

    assert found == job
    assert job.status == "queued"
    assert job.params == {"file_path": "/bags/a.mcap"}
    assert job.created_at.tzinfo is not None
    assert job.progress is None and job.cancel_requested is False


def test_claim_takes_the_oldest_and_marks_it_running(sqlite_engine):
    with sqlite_engine.begin() as c:
        first = enqueue(c, "ingest", {"n": 1})
        enqueue(c, "ingest", {"n": 2})
        claimed = claim_next(c)

    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status == "running"
    assert claimed.started_at is not None


def test_claim_on_an_empty_queue(sqlite_engine):
    with sqlite_engine.begin() as c:
        assert claim_next(c) is None


def test_progress_and_finish(sqlite_engine):
    progress = Progress(
        topics=[TopicProgress(name="/imu", done=5, total=10, status=None)],
        done=5,
        total=10,
        finished=False,
    )
    with sqlite_engine.begin() as c:
        job = enqueue(c, "ingest", {})
        save_progress(c, job.id, progress)
        finish(c, job.id, "failed", "boom")
        found = get_job(c, job.id)

    assert found is not None
    assert found.progress == progress
    assert (found.status, found.error) == ("failed", "boom")
    assert found.finished_at is not None


def test_cancel_a_queued_job_at_once(sqlite_engine):
    with sqlite_engine.begin() as c:
        job = enqueue(c, "ingest", {})
        request_cancel(c, job.id)
        found = get_job(c, job.id)

    assert found is not None
    assert found.status == "cancelled"
    assert found.cancel_requested is False


def test_cancel_a_running_job_sets_the_flag(sqlite_engine):
    with sqlite_engine.begin() as c:
        job = enqueue(c, "ingest", {})
        claim_next(c)
        request_cancel(c, job.id)
        found = get_job(c, job.id)

    assert found is not None
    assert (found.status, found.cancel_requested) == ("running", True)


def test_running_jobs_of_a_stopped_worker_are_failed(sqlite_engine):
    with sqlite_engine.begin() as c:
        job = enqueue(c, "ingest", {})
        enqueue(c, "ingest", {})
        claim_next(c)
        count = fail_interrupted(c)
        found = get_job(c, job.id)
        statuses = sorted(j.status for j in list_jobs(c))

    assert count == 1
    assert found is not None
    assert (found.status, found.error) == ("failed", INTERRUPTED_ERROR)
    assert statuses == ["failed", "queued"]


def test_list_jobs_newest_first(sqlite_engine):
    with sqlite_engine.begin() as c:
        older = enqueue(c, "ingest", {"n": 1})
        newer = enqueue(c, "ingest", {"n": 2})
        listed = [j.id for j in list_jobs(c)]

    assert listed == [newer.id, older.id]

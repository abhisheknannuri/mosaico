from datetime import datetime, timezone

from mosaico_dashboard.db.jobs import claim_next, get_job
from mosaico_dashboard.domain.models import BagFile, IngestRequest
from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.ingestion import (
    INGEST_JOB,
    cancel_job,
    enqueue_ingestion,
    run_job,
)

NEW = IngestRequest(file_path="/bags/new.mcap", sequence_name="new_run")
FILE = BagFile(
    relative_path="new.mcap",
    path="/bags/new.mcap",
    size_bytes=1,
    modified_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    recording_name="new__mcap",
)


def claimed(engine, request=NEW):
    job = enqueue_ingestion(engine, request)
    with engine.begin() as c:
        claim_next(c)
    return job


def reload(engine, job_id):
    with engine.begin() as c:
        job = get_job(c, job_id)
    assert job is not None
    return job


def test_enqueue_stores_the_request(sqlite_engine):
    job = enqueue_ingestion(sqlite_engine, NEW)

    assert job.kind == INGEST_JOB
    assert IngestRequest.model_validate(job.params) == NEW


def test_run_records_progress_and_completion(sqlite_engine):
    job = claimed(sqlite_engine)

    run_job(FakeGateway(), sqlite_engine, job.id)

    done = reload(sqlite_engine, job.id)
    assert done.status == "completed"
    assert done.progress is not None
    assert (done.progress.done, done.progress.total, done.progress.finished) == (
        10,
        10,
        True,
    )


def test_run_records_the_error(sqlite_engine):
    job = claimed(
        sqlite_engine,
        IngestRequest(file_path="/bags/a.mcap", sequence_name="r2b_galileo2_0"),
    )

    run_job(FakeGateway(), sqlite_engine, job.id)

    failed = reload(sqlite_engine, job.id)
    assert failed.status == "failed"
    assert failed.error is not None and "already exists" in failed.error


def test_ctrl_c_during_the_run_is_a_cancellation(sqlite_engine):
    class InterruptedGateway(FakeGateway):
        def ingest(self, request, on_progress):
            raise KeyboardInterrupt

    job = claimed(sqlite_engine)

    run_job(InterruptedGateway(), sqlite_engine, job.id)

    assert reload(sqlite_engine, job.id).status == "cancelled"


def test_cancel_job(sqlite_engine):
    job = enqueue_ingestion(sqlite_engine, NEW)

    cancelled = cancel_job(sqlite_engine, job.id)

    assert cancelled is not None and cancelled.status == "cancelled"
    assert cancel_job(sqlite_engine, "missing") is None


def test_error_hints():
    from mosaico_dashboard.services.ingestion import error_hint

    assert "Choose another name" in (error_hint("Flight returned already exists") or "")
    assert "could not be reached" in (error_hint("FlightUnavailableError: x") or "")
    assert "write permission" in (error_hint("Unauthenticated") or "")
    assert error_hint("something else") is None
    assert error_hint(None) is None


def test_start_queues_when_every_topic_is_accepted(sqlite_engine):
    from mosaico_dashboard.gateway.fake import sample_dry_run
    from mosaico_dashboard.services.ingestion import start_ingestion

    gateway = FakeGateway(dry_run_topics=sample_dry_run()[:2])

    result, job = start_ingestion(gateway, sqlite_engine, FILE, "run", [], [], False)

    assert result.verdict == "ok"
    assert job is not None and job.status == "queued"
    assert job.params["keep_partial"] is False


def test_start_needs_confirmation_when_topics_are_skipped(sqlite_engine):
    from mosaico_dashboard.services.ingestion import start_ingestion

    _, unconfirmed = start_ingestion(
        FakeGateway(), sqlite_engine, FILE, "run", [], [], False
    )
    _, confirmed = start_ingestion(
        FakeGateway(), sqlite_engine, FILE, "run", [], [], True
    )

    assert unconfirmed is None
    assert confirmed is not None


def test_start_does_not_queue_a_blocked_file(sqlite_engine):
    from mosaico_dashboard.services.ingestion import start_ingestion

    result, job = start_ingestion(
        FakeGateway(), sqlite_engine, FILE, "bad name", [], [], True
    )

    assert job is None and result.error is not None


def test_active_ingestion_prefers_the_running_job(sqlite_engine):
    from mosaico_dashboard.services.ingestion import get_active_ingestion

    assert get_active_ingestion(sqlite_engine) is None
    first = enqueue_ingestion(sqlite_engine, NEW)
    second = enqueue_ingestion(sqlite_engine, NEW)
    assert (active := get_active_ingestion(sqlite_engine)) and active.id == first.id
    with sqlite_engine.begin() as c:
        claim_next(c)
        claim_next(c)
        from mosaico_dashboard.db.jobs import finish

        finish(c, first.id, "completed")
    assert (active := get_active_ingestion(sqlite_engine)) and active.id == second.id


def test_list_ingestions_is_none_when_the_database_is_down():
    from mosaico_dashboard.db.engine import create_db_engine
    from mosaico_dashboard.services.ingestion import list_ingestions

    engine = create_db_engine("postgresql+psycopg://x:x@127.0.0.1:1/x")

    assert list_ingestions(engine) is None

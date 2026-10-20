from mosaico_dashboard.db.jobs import claim_next, get_job
from mosaico_dashboard.domain.models import IngestRequest
from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.ingestion import (
    INGEST_JOB,
    cancel_job,
    enqueue_ingestion,
    run_job,
)

NEW = IngestRequest(file_path="/bags/new.mcap", sequence_name="new_run")


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

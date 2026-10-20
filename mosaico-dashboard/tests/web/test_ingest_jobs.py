import pytest
from fastapi.testclient import TestClient

from mosaico_dashboard.db.jobs import claim_next, finish, save_progress
from mosaico_dashboard.domain.models import IngestRequest, Progress, TopicProgress
from mosaico_dashboard.gateway.fake import FakeGateway, sample_dry_run
from mosaico_dashboard.main import create_app
from mosaico_dashboard.services.ingestion import enqueue_ingestion
from mosaico_dashboard.settings import Settings

from .conftest import memory_engine

FORM = {"file": "drive.mcap", "sequence_name": "drive__mcap"}
REQUEST = IngestRequest(file_path="/bags/drive.mcap", sequence_name="drive__mcap")


@pytest.fixture
def bags(tmp_path):
    folder = tmp_path / "bags"
    folder.mkdir()
    (folder / "drive.mcap").write_bytes(b"x")
    return folder


def make(folder, gateway=None) -> TestClient:
    app = create_app(
        Settings(ingest_dir=folder),
        gateway=gateway or FakeGateway(),
        engine=memory_engine(),
    )
    return TestClient(app)


def engine_of(client):
    return client.app.state.engine


def test_dry_run_offers_start(bags):
    text = make(bags).post("/ingest/dry-run", data=FORM).text

    assert 'hx-post="/ingest/start"' in text
    assert 'name="skipped_confirmed"' in text


def test_start_with_skipped_topics_asks_for_confirmation(bags):
    response = make(bags).post("/ingest/start", data=FORM)

    assert "HX-Redirect" not in response.headers
    assert "Tick the box" in response.text


def test_start_queues_the_job_and_redirects(bags):
    client = make(bags)

    response = client.post("/ingest/start", data=FORM | {"skipped_confirmed": "true"})

    assert response.headers["HX-Redirect"].startswith("/ingest/jobs/")
    page = client.get(response.headers["HX-Redirect"]).text
    assert "Ingestion: drive__mcap" in page
    assert 'sse-connect="/ingest/jobs/' in page
    assert "htmx-ext-sse-2.2.4.js" in page
    assert "Waiting" in page


def test_start_without_skipped_topics_needs_no_confirmation(bags):
    gateway = FakeGateway(dry_run_topics=sample_dry_run()[:2])

    response = make(bags, gateway).post("/ingest/start", data=FORM)

    assert "HX-Redirect" in response.headers


def test_job_page_shows_progress_per_topic(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)
    progress = Progress(
        topics=[TopicProgress(name="/imu", done=50, total=200, status=None)],
        done=50,
        total=200,
        finished=False,
    )
    with engine_of(client).begin() as c:
        claim_next(c)
        save_progress(c, job.id, progress)

    text = client.get(f"/ingest/jobs/{job.id}").text

    assert "Ingesting" in text and "25%" in text
    assert "50 / 200" in text
    assert f'hx-post="/ingest/jobs/{job.id}/cancel"' in text


def test_failed_job_shows_the_error_and_a_hint(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)
    with engine_of(client).begin() as c:
        finish(c, job.id, "failed", "Flight returned already exists error")

    text = client.get(f"/ingest/jobs/{job.id}").text

    assert "Ingestion failed" in text
    assert "Choose another name" in text
    assert "Nothing was kept" not in text
    assert "sse-connect" not in text


def test_cancel(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)

    text = client.post(f"/ingest/jobs/{job.id}/cancel").text

    assert "Cancelled" in text


def test_events_stream_the_progress_and_end_when_finished(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)
    with engine_of(client).begin() as c:
        finish(c, job.id, "completed")

    response = client.get(f"/ingest/jobs/{job.id}/events")

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith("event: progress\ndata: ")
    assert "Ingested" in response.text
    assert response.text.endswith("event: done\ndata: \n\n")


def test_unknown_job(bags):
    client = make(bags)

    assert client.get("/ingest/jobs/nope").status_code == 404
    assert client.post("/ingest/jobs/nope/cancel").status_code == 404


def test_top_bar_shows_the_active_ingestion(bags):
    client = make(bags)
    assert client.get("/ingest/active").text.strip() == ""

    job = enqueue_ingestion(engine_of(client), REQUEST)

    text = client.get("/ingest/active").text
    assert f'href="/ingest/jobs/{job.id}"' in text
    assert "Queued: drive__mcap" in text
    assert 'hx-get="/ingest/active"' in client.get("/").text

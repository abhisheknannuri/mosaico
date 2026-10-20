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

    assert "HX-Push-Url" not in response.headers
    assert "Tick the box" in response.text


def test_start_queues_the_job_and_shows_it_in_the_right_panel(bags):
    client = make(bags)

    response = client.post("/ingest/start", data=FORM | {"skipped_confirmed": "true"})

    assert response.headers["HX-Retarget"] == "#ingest-detail"
    assert response.headers["HX-Push-Url"].startswith("/ingest?job=")
    assert 'sse-connect="/ingest/jobs/' in response.text
    page = client.get(response.headers["HX-Push-Url"]).text
    assert "drive__mcap" in page and "Waiting" in page
    assert "htmx-ext-sse-2.2.4.js" in page


def test_start_without_skipped_topics_needs_no_confirmation(bags):
    gateway = FakeGateway(dry_run_topics=sample_dry_run()[:2])

    response = make(bags, gateway).post("/ingest/start", data=FORM)

    assert "HX-Push-Url" in response.headers


def test_old_job_url_redirects_to_the_ingest_page(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)

    response = client.get(f"/ingest/jobs/{job.id}", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/ingest?job={job.id}"


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

    text = client.get(f"/ingest?job={job.id}").text

    assert "Ingesting" in text and "25%" in text
    assert "50 / 200" in text
    assert f'hx-post="/ingest/jobs/{job.id}/cancel"' in text


def test_failed_job_shows_the_error_and_a_hint(bags):
    client = make(bags)
    job = enqueue_ingestion(engine_of(client), REQUEST)
    with engine_of(client).begin() as c:
        finish(c, job.id, "failed", "Flight returned already exists error")

    text = client.get(f"/ingest/detail?job={job.id}").text

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


def test_top_bar_shows_the_active_ingestion_and_polls_slowly_when_idle(bags):
    client = make(bags)
    idle = client.get("/ingest/active").text
    assert "every 30s" in idle and "Queued" not in idle

    job = enqueue_ingestion(engine_of(client), REQUEST)

    text = client.get("/ingest/active").text
    assert f'href="/ingest?job={job.id}"' in text
    assert "Queued: drive__mcap" in text
    assert "every 3s" in text
    assert 'hx-get="/ingest/active"' in client.get("/").text


def test_history_lists_recent_ingestions(bags):
    client = make(bags)
    engine = engine_of(client)
    done = enqueue_ingestion(engine, REQUEST)
    failed = enqueue_ingestion(
        engine, REQUEST.model_copy(update={"sequence_name": "other"})
    )
    with engine.begin() as c:
        claim_next(c)
        finish(c, done.id, "completed")
        claim_next(c)
        finish(c, failed.id, "failed", "Flight returned already exists error")

    text = client.get("/ingest/history").text

    assert f'href="/ingest?job={done.id}"' in text
    assert '<span class="chip ok">completed</span>' in text
    assert "failed</span>" in text and "already exists" in text
    assert text.index("other") < text.index(">drive__mcap<")


def test_history_when_empty(bags):
    assert "No ingestions yet." in make(bags).get("/ingest/history").text


def test_history_when_the_database_is_down(bags):
    from mosaico_dashboard.db.engine import create_db_engine

    engine = create_db_engine("postgresql+psycopg://x:x@127.0.0.1:1/x")
    app = create_app(Settings(ingest_dir=bags), gateway=FakeGateway(), engine=engine)

    client = TestClient(app)

    assert "drive.mcap" in client.get("/ingest").text
    assert "database is not reachable" in client.get("/ingest/history").text


def test_advanced_options_with_defaults_from_settings(bags):
    app = create_app(
        Settings(
            ingest_dir=bags, ingest_ros_distro="ros2_humble", ingest_keep_partial=True
        ),
        gateway=FakeGateway(),
        engine=memory_engine(),
    )

    text = TestClient(app).get("/ingest", params={"file": "drive.mcap"}).text

    assert "Advanced options" in text
    assert '<option value="ros2_humble" selected>' in text
    assert 'name="keep_partial" value="true" checked' in text
    assert 'name="update_if_exists"' in text


def test_dry_run_lets_the_user_pick_topics(bags):
    text = make(bags).post("/ingest/dry-run", data=FORM).text

    assert 'name="topics_chosen" value="true"' in text
    assert 'type="checkbox" name="topic" value="/imu/data" checked' in text
    assert 'type="hidden" name="topic" value="/robot/custom"' in text


def test_start_with_topics_left_out(bags):
    client = make(bags)
    data = FORM | {
        "topics_chosen": "true",
        "topic": ["/imu/data", "/robot/custom"],
        "skipped_confirmed": "true",
        "ros_distro": "ros2_jazzy",
        "update_if_exists": "true",
    }

    response = client.post("/ingest/start", data=data)

    job_id = response.headers["HX-Push-Url"].split("job=", 1)[1]
    from mosaico_dashboard.services.ingestion import get_ingestion

    job = get_ingestion(engine_of(client), job_id)
    assert job is not None
    assert job.params["topics"] == ["/imu/data", "/robot/custom"]
    assert job.params["ros_distro"] == "ros2_jazzy"
    assert job.params["update_if_exists"] is True


def test_start_with_no_topic_selected(bags):
    data = FORM | {"topics_chosen": "true", "topic": ["/robot/custom"]}

    text = make(bags).post("/ingest/start", data=data).text

    assert "No topic selected" in text


def test_tabs_switch_without_leaving_the_page(bags):
    client = make(bags)

    page = client.get("/ingest").text
    fragment = client.get("/ingest/watchdog", headers={"HX-Request": "true"}).text

    assert 'href="/ingest/watchdog"' in page and 'href="/ingest/history"' in page
    assert 'hx-target="#ingest-tab"' in page
    assert "<html" not in fragment
    assert "Start watchdog" in fragment and "disabled" in fragment
    assert "drive.mcap" in fragment


def test_detail_panel_for_a_file(bags):
    text = make(bags).get("/ingest/detail", params={"file": "drive.mcap"}).text

    assert "<html" not in text
    assert 'name="sequence_name" value="drive__mcap"' in text


def test_activity_bar(bags):
    client = make(bags)
    assert "Idle" in client.get("/ingest/activity").text
    assert "every 15s" in client.get("/ingest/activity").text

    job = enqueue_ingestion(engine_of(client), REQUEST)
    enqueue_ingestion(engine_of(client), REQUEST)
    with engine_of(client).begin() as c:
        claim_next(c)

    text = client.get("/ingest/activity").text
    assert "Ingesting" in text and "drive__mcap" in text
    assert "1 more queued" in text
    assert f'hx-get="/ingest/detail?job={job.id}"' in text
    assert "every 2s" in text
    assert 'id="ingest-activity"' in client.get("/ingest").text


def test_search_box_and_counts(bags):
    text = make(bags).get("/ingest").text

    assert 'oninput="filterFiles(this)"' in text
    assert 'data-name="drive.mcap"' in text
    assert "1 files" in text

import pytest
from fastapi.testclient import TestClient

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings

from .conftest import memory_engine


@pytest.fixture
def bags(tmp_path):
    folder = tmp_path / "bags"
    (folder / "run_01").mkdir(parents=True)
    (folder / "run_01" / "drive.mcap").write_bytes(b"x" * 2048)
    return folder


def client_for(folder) -> TestClient:
    settings = Settings(ingest_dir=folder)
    return TestClient(
        create_app(settings, gateway=FakeGateway(), engine=memory_engine())
    )


def test_without_a_folder_the_page_says_how_to_set_it(client):
    text = client.get("/ingest").text

    assert "No folder set" in text
    assert "DASHBOARD_INGEST_DIR" in text


def test_missing_folder(tmp_path):
    text = client_for(tmp_path / "nope").get("/ingest").text

    assert "doesn't exist" in text


def test_lists_the_files_with_links(bags):
    text = client_for(bags).get("/ingest").text

    assert str(bags) in text
    assert "run_01/drive.mcap" in text
    assert 'href="/ingest?file=run_01/drive.mcap"' in text
    assert "2.05 kB" in text
    assert "Select a file" in text


def test_selecting_a_file_shows_its_options(bags):
    text = client_for(bags).get("/ingest", params={"file": "run_01/drive.mcap"}).text

    assert 'aria-selected="true"' in text
    assert 'name="sequence_name" value="run_01-drive__mcap"' in text
    assert 'name="metadata_key"' in text


def test_selection_is_a_fragment_for_htmx(bags):
    response = client_for(bags).get(
        "/ingest", params={"file": "run_01/drive.mcap"}, headers={"HX-Request": "true"}
    )

    assert "<html" not in response.text
    assert 'id="ingest-tab"' in response.text


def test_a_file_outside_the_listing_is_not_selected(bags):
    text = client_for(bags).get("/ingest", params={"file": "../secret.mcap"}).text

    assert 'name="sequence_name"' not in text


DRY_RUN = "/ingest/dry-run"
FORM = {"file": "run_01/drive.mcap", "sequence_name": "run_01-drive__mcap"}


def client_with(folder, gateway) -> TestClient:
    settings = Settings(ingest_dir=folder)
    return TestClient(create_app(settings, gateway=gateway, engine=memory_engine()))


def test_options_post_a_dry_run(bags):
    text = client_for(bags).get("/ingest", params={"file": "run_01/drive.mcap"}).text

    assert 'hx-post="/ingest/dry-run"' in text
    assert ">Dry run</button>" in text
    assert 'id="dry-run"' in text


def test_dry_run_with_skipped_topics_warns(bags):
    text = client_for(bags).post(DRY_RUN, data=FORM).text

    assert "1 of 3 topics would be skipped" in text
    assert "12,600 messages" in text
    assert "/robot/custom" in text and "Unresolved adapter" in text
    assert "<html" not in text


def test_dry_run_with_every_topic_accepted(bags):
    from mosaico_dashboard.gateway.fake import sample_dry_run

    gateway = FakeGateway(dry_run_topics=sample_dry_run()[:2])

    text = client_with(bags, gateway).post(DRY_RUN, data=FORM).text

    assert "Ready to ingest" in text
    assert "All 2 topics, 12,600 messages" in text


def test_dry_run_without_accepted_topics_is_blocked(bags):
    from mosaico_dashboard.gateway.fake import sample_dry_run

    gateway = FakeGateway(dry_run_topics=sample_dry_run()[2:])

    text = client_with(bags, gateway).post(DRY_RUN, data=FORM).text

    assert "No topic can be ingested" in text


def test_dry_run_reports_an_invalid_name(bags):
    text = client_for(bags).post(DRY_RUN, data=FORM | {"sequence_name": "my run"}).text

    assert "Can&#39;t run the dry run" in text
    assert "space" in text


def test_dry_run_sends_metadata_rows(bags):
    data = FORM | {"metadata_key": ["project", ""], "metadata_value": ["wh", ""]}

    response = client_for(bags).post(DRY_RUN, data=data)

    assert response.status_code == 200
    assert "would be skipped" in response.text


def test_dry_run_of_a_file_not_in_the_folder(bags):
    text = client_for(bags).post(DRY_RUN, data=FORM | {"file": "../x.mcap"}).text

    assert "not in the ingest folder" in text

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


def test_without_a_folder_the_page_asks_to_choose_one(client):
    text = client.get("/ingest").text

    assert "No folder chosen" in text
    assert 'hx-get="/ingest/folders?tab=manual"' in text


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


def test_folder_dialog_lists_folders_and_files(bags):
    (bags / "notes.txt").write_bytes(b"x")

    text = client_for(bags).get("/ingest/folders?tab=watchdog").text

    assert f'id="folder-selection" name="path" value="{bags}"' in text
    assert f'data-path="{bags}/run_01"' in text
    assert "notes.txt" in text
    assert 'id="folder-tab" name="tab" value="watchdog"' in text


def test_choosing_a_folder_saves_it_and_reloads_the_tab(bags):
    client = client_for(bags)

    response = client.post(
        "/ingest/folder", data={"path": str(bags / "run_01"), "tab": "watchdog"}
    )

    assert response.headers["HX-Redirect"] == "/ingest/watchdog"
    text = client.get("/ingest").text
    assert f"{bags}/run_01" in text
    assert 'data-name="drive.mcap"' in text


def test_choosing_a_missing_folder_shows_why(bags):
    response = client_for(bags).post("/ingest/folder", data={"path": "/nope/bags"})

    assert "HX-Redirect" not in response.headers
    assert "doesn&#39;t exist or isn&#39;t a folder" in response.text


def test_default_folder_is_a_place_once_another_is_chosen(bags):
    client = client_for(bags)
    assert "Default (.env)" not in client.get("/ingest/folders").text

    client.post("/ingest/folder", data={"path": str(bags / "run_01")})
    assert "Default (.env)" in client.get("/ingest/folders").text

    client.post("/ingest/folder", data={"path": str(bags)})
    assert 'data-name="run_01/drive.mcap"' in client.get("/ingest").text

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

    assert "No ingest folder set" in text
    assert "DASHBOARD_INGEST_DIR" in text


def test_missing_folder(tmp_path):
    text = client_for(tmp_path / "nope").get("/ingest").text

    assert "Ingest folder not found" in text


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
    assert 'id="ingest"' in response.text


def test_a_file_outside_the_listing_is_not_selected(bags):
    text = client_for(bags).get("/ingest", params={"file": "../secret.mcap"}).text

    assert 'name="sequence_name"' not in text

from fastapi.testclient import TestClient

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings


def test_recordings_page_lists_recordings(client):
    response = client.get("/recordings")

    assert response.status_code == 200
    assert "<html" in response.text
    assert "r2b_galileo2_0" in response.text
    assert "r2b_robotarm_0" in response.text


def test_rows_show_formatted_values_and_sensor_chips(client):
    text = client.get("/recordings").text

    assert "10 May 2024, 00:27 UTC" in text
    assert "20.5 s" in text
    assert "598 MB" in text
    assert "598,200,000 bytes" in text
    assert '<span class="chip">Camera</span>' in text


def test_htmx_request_returns_table_only(client):
    response = client.get("/recordings", headers={"HX-Request": "true"})

    assert "<html" not in response.text
    assert 'id="recordings"' in response.text


def test_empty_catalog_shows_hint():
    client = TestClient(
        create_app(Settings(), gateway=FakeGateway(recordings=[], streams=[]))
    )

    text = client.get("/recordings").text

    assert "No recordings yet" in text
    assert "<table" not in text


def test_nav_links_to_recordings(client):
    assert 'href="/recordings"' in client.get("/").text

from fastapi.testclient import TestClient

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings


def test_overview_shows_totals(client):
    text = client.get("/").text

    assert "Recordings" in text
    assert "778 MB" in text
    assert "778,430,000 bytes" in text
    assert "across all recordings" in text
    assert "Sensor streams" in text


def test_overview_shows_storage_by_sensor_type(client):
    text = client.get("/").text

    assert 'class="bar-list"' in text
    assert "Camera" in text


def test_overview_lists_latest_recordings(client):
    text = client.get("/").text

    assert "r2b_robotarm_0" in text
    assert 'href="/recordings"' in text


def test_overview_empty_catalog():
    client = TestClient(
        create_app(Settings(), gateway=FakeGateway(recordings=[], streams=[]))
    )

    text = client.get("/").text

    assert "No recordings yet" in text
    assert 'class="stats"' not in text

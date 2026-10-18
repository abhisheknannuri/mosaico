from fastapi.testclient import TestClient

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings


def client_with_daemon_down() -> TestClient:
    return TestClient(create_app(Settings(), gateway=FakeGateway(available=False)))


def test_readyz_ok(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mosaicod_version": "0.8.0-dev"}


def test_readyz_unavailable():
    response = client_with_daemon_down().get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "mosaicod_version": None}


def test_readyz_documents_503(client):
    responses = client.get("/openapi.json").json()["paths"]["/readyz"]["get"][
        "responses"
    ]

    assert "503" in responses


def test_status_fragment_connected(client):
    response = client.get("/status")

    assert "<html" not in response.text
    assert "status-dot ok" in response.text
    assert "mosaicod 0.8.0-dev" in response.text


def test_status_fragment_unreachable():
    response = client_with_daemon_down().get("/status")

    assert "status-dot down" in response.text
    assert "mosaicod unreachable" in response.text


def test_pages_load_status_with_htmx(client):
    assert 'hx-get="/status"' in client.get("/").text


def test_status_is_not_in_openapi(client):
    assert "/status" not in client.get("/openapi.json").json()["paths"]

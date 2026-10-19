def test_readyz_ok(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mosaicod": "ok",
        "mosaicod_version": "0.8.0-dev",
        "database": "ok",
    }


def test_readyz_unavailable_when_mosaicod_is_down(client_daemon_down):
    response = client_daemon_down.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "mosaicod": "unavailable",
        "mosaicod_version": None,
        "database": "ok",
    }


def test_readyz_unavailable_when_the_database_is_down(client_database_down):
    response = client_database_down.get("/readyz")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert response.json()["mosaicod"] == "ok"


def test_pages_still_work_when_the_database_is_down(client_database_down):
    assert client_database_down.get("/recordings").status_code == 200


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


def test_status_fragment_unreachable(client_daemon_down):
    response = client_daemon_down.get("/status")

    assert "status-dot down" in response.text
    assert "mosaicod unreachable" in response.text


def test_pages_load_status_with_htmx(client):
    assert 'hx-get="/status"' in client.get("/").text


def test_status_is_not_in_openapi(client):
    assert "/status" not in client.get("/openapi.json").json()["paths"]

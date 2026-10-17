def test_openapi_metadata(client):
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Mosaico Dashboard"
    assert schema["info"]["version"] == "0.1.0"


def test_healthz_is_documented(client):
    operation = client.get("/openapi.json").json()["paths"]["/healthz"]["get"]

    assert operation["operationId"] == "healthz"
    assert operation["tags"] == ["ops"]
    assert operation["summary"] == "Process liveness"


def test_swagger_ui_is_served(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()

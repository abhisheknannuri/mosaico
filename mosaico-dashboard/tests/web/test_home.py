def test_home_returns_full_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "<html" in response.text
    assert "htmx-2.0.11.min.js" in response.text
    assert 'id="home-status"' in response.text


def test_htmx_request_returns_fragment_only(client):
    response = client.get("/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="home-status"' in response.text


def test_boosted_link_returns_full_page(client):
    response = client.get("/", headers={"HX-Request": "true", "HX-Boosted": "true"})

    assert "<html" in response.text


def test_history_restore_returns_full_page(client):
    headers = {"HX-Request": "true", "HX-History-Restore-Request": "true"}
    response = client.get("/", headers=headers)

    assert "<html" in response.text


def test_response_varies_on_hx_request(client):
    response = client.get("/")

    assert response.headers["Vary"] == "HX-Request"


def test_static_files_are_served(client):
    assert client.get("/static/vendor/htmx-2.0.11.min.js").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200


def test_html_pages_are_not_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "/" not in paths

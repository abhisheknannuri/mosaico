def test_full_page_includes_layout_and_htmx(client):
    response = client.get("/recordings")

    assert "<html" in response.text
    assert "htmx-2.0.11.min.js" in response.text
    assert 'class="sidebar"' in response.text


def test_htmx_request_returns_fragment_only(client):
    response = client.get("/recordings", headers={"HX-Request": "true"})

    assert "<html" not in response.text
    assert 'id="recordings"' in response.text


def test_boosted_link_returns_full_page(client):
    headers = {"HX-Request": "true", "HX-Boosted": "true"}

    assert "<html" in client.get("/recordings", headers=headers).text


def test_history_restore_returns_full_page(client):
    headers = {"HX-Request": "true", "HX-History-Restore-Request": "true"}

    assert "<html" in client.get("/recordings", headers=headers).text


def test_response_varies_on_hx_request(client):
    assert client.get("/recordings").headers["Vary"] == "HX-Request"


def test_static_files_are_served(client):
    for path in [
        "/static/vendor/htmx-2.0.11.min.js",
        "/static/css/app.css",
        "/static/js/app.js",
        "/static/img/mosaico-logo.svg",
    ]:
        assert client.get(path).status_code == 200, path


def test_html_pages_are_not_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "/" not in paths
    assert "/recordings" not in paths

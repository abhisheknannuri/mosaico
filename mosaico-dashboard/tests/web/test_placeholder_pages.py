import pytest


@pytest.mark.parametrize("path, title", [("/export", "Export")])
def test_placeholder_page(client, path, title):
    response = client.get(path)

    assert response.status_code == 200
    assert f"<h1>{title}</h1>" in response.text
    assert "Coming soon" in response.text


def test_placeholder_fragment_for_htmx(client):
    text = client.get("/export", headers={"HX-Request": "true"}).text

    assert "Coming soon" in text
    assert "<html" not in text

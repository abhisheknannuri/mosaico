import re


def current_page_link(html: str) -> str:
    match = re.search(r'<a href="([^"]+)"[^>]*aria-current="page"', html)
    assert match, "no sidebar link is marked as the current page"
    return match.group(1)


def test_sidebar_marks_current_page(client):
    assert current_page_link(client.get("/").text) == "/"
    assert current_page_link(client.get("/recordings").text) == "/recordings"


def test_sidebar_has_icons_and_api_docs_link(client):
    html = client.get("/").text

    assert html.count('class="lucide') >= 4
    assert 'href="/docs"' in html


def test_collapsed_state_is_restored_before_render(client):
    head = client.get("/").text.split("</head>")[0]

    assert 'localStorage.getItem("nav")' in head
    assert "nav-collapsed" in head

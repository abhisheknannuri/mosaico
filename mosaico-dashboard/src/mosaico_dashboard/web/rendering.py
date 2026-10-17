"""Jinja2 templates and page-or-fragment rendering for htmx."""

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def wants_fragment(request: Request) -> bool:
    """True for htmx requests that swap part of a page (not boosted links or history restores)."""
    headers = request.headers
    return (
        headers.get("HX-Request") == "true"
        and headers.get("HX-Boosted") != "true"
        and headers.get("HX-History-Restore-Request") != "true"
    )


def render(
    request: Request, page: str, fragment: str, context: dict[str, Any]
) -> HTMLResponse:
    """Render the full page, or only the fragment template for htmx requests."""
    template = fragment if wants_fragment(request) else page
    response = templates.TemplateResponse(request, template, context)
    response.headers["Vary"] = "HX-Request"
    return response

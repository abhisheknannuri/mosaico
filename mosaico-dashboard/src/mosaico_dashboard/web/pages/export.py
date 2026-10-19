"""Export page."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.web.rendering import render

router = APIRouter(include_in_schema=False)


@router.get("/export", response_class=HTMLResponse)
def export(request: Request) -> HTMLResponse:
    return render(request, "pages/export.html", "partials/export.html", {})

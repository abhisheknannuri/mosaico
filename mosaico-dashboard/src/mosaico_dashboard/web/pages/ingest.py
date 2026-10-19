"""Ingest page."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.web.rendering import render

router = APIRouter(include_in_schema=False)


@router.get("/ingest", response_class=HTMLResponse)
def ingest(request: Request) -> HTMLResponse:
    return render(request, "pages/ingest.html", "partials/ingest.html", {})

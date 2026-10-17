"""Home page."""

from datetime import datetime
from importlib.metadata import version

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.web.rendering import render

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    context = {
        "version": version("mosaico-dashboard"),
        "rendered_at": datetime.now().strftime("%H:%M:%S"),
    }
    return render(request, "pages/home.html", "partials/home_status.html", context)

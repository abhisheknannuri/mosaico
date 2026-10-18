"""Recordings list."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.recordings import list_recording_summaries
from mosaico_dashboard.web.dependencies import get_gateway
from mosaico_dashboard.web.rendering import render

router = APIRouter(include_in_schema=False)


@router.get("/recordings", response_class=HTMLResponse)
def recordings(
    request: Request, gateway: MosaicoGateway = Depends(get_gateway)
) -> HTMLResponse:
    context = {"summaries": list_recording_summaries(gateway)}
    return render(
        request, "pages/recordings.html", "partials/recordings_table.html", context
    )

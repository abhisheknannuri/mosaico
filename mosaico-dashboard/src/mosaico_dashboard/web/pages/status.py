"""mosaicod connection indicator shown in the header."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.status import get_daemon_status
from mosaico_dashboard.web.dependencies import get_gateway
from mosaico_dashboard.web.rendering import templates

router = APIRouter(include_in_schema=False)


@router.get("/status", response_class=HTMLResponse)
def daemon_status(
    request: Request, gateway: MosaicoGateway = Depends(get_gateway)
) -> HTMLResponse:
    context = {"status": get_daemon_status(gateway)}
    return templates.TemplateResponse(request, "partials/daemon_status.html", context)

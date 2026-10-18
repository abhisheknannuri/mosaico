"""Overview (home) page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.overview import get_overview
from mosaico_dashboard.web.dependencies import get_gateway
from mosaico_dashboard.web.rendering import render

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def overview(
    request: Request, gateway: MosaicoGateway = Depends(get_gateway)
) -> HTMLResponse:
    context = {"overview": get_overview(gateway)}
    return render(request, "pages/overview.html", "partials/overview.html", context)

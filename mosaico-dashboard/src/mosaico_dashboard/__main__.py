"""Run command: `poetry run mosaico-dashboard` or `python -m mosaico_dashboard`."""

import uvicorn

from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.settings import get_settings


def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    uvicorn.run(
        "mosaico_dashboard.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,
    )


if __name__ == "__main__":
    run()

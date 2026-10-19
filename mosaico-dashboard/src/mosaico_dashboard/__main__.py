"""Run command: `poetry run mosaico-dashboard` or `python -m mosaico_dashboard`."""

import uvicorn

from mosaico_dashboard.db.migrate import upgrade_to_head
from mosaico_dashboard.logging_config import get_logger, setup_logging
from mosaico_dashboard.settings import get_settings

logger = get_logger(__name__)


def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    if settings.migrate_on_start:
        try:
            upgrade_to_head(settings.database_url)
        except Exception as error:
            logger.warning(
                "Database migrations not applied (%s); ingestion and export are "
                "unavailable until the database is reachable.",
                error,
            )
    uvicorn.run(
        "mosaico_dashboard.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,
    )


if __name__ == "__main__":
    run()

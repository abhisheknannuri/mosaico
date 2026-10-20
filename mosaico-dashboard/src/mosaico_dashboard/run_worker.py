"""Worker command: `poetry run mosaico-dashboard-worker`."""

import signal

from mosaico_dashboard.db.migrate import upgrade_to_head
from mosaico_dashboard.factories import build_engine
from mosaico_dashboard.jobs.worker import Worker
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
            logger.warning("Database migrations not applied (%s)", error)
    engine = build_engine(settings)
    worker = Worker(engine, settings.worker_poll_seconds)
    signal.signal(signal.SIGTERM, lambda *_: worker.stop())
    signal.signal(signal.SIGINT, lambda *_: worker.stop())
    logger.info("Worker started")
    try:
        worker.run()
    finally:
        engine.dispose()
        logger.info("Worker stopped")


if __name__ == "__main__":
    run()

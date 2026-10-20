"""Child process of the worker: `python -m mosaico_dashboard.jobs.run_job <job id>`."""

import sys

from mosaico_dashboard.factories import build_engine, build_gateway
from mosaico_dashboard.logging_config import setup_logging
from mosaico_dashboard.services.ingestion import run_job
from mosaico_dashboard.settings import get_settings


def main(job_id: str) -> None:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    gateway = build_gateway(settings)
    engine = build_engine(settings)
    try:
        run_job(gateway, engine, job_id)
    finally:
        gateway.close()
        engine.dispose()


if __name__ == "__main__":
    main(sys.argv[1])

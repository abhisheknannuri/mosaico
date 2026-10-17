"""Process-wide logging: dashboard, uvicorn and Mosaico SDK logs go to one console handler."""

import logging
import sys
from typing import Literal

from rich.logging import RichHandler

PLAIN_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
PLAIN_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LogFormat = Literal["plain", "pretty"]


def setup_logging(level: str = "INFO", log_format: LogFormat = "plain") -> None:
    """Configure the root logger: `plain` (SDK format) or `pretty` (Rich colours)."""
    if log_format == "pretty":
        handler: logging.Handler = RichHandler(
            rich_tracebacks=True, log_time_format="[%X]"
        )
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(PLAIN_FORMAT, PLAIN_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

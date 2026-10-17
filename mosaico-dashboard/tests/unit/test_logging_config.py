import logging

from rich.logging import RichHandler

from mosaico_dashboard.logging_config import setup_logging


def test_plain_logging_has_one_handler():
    setup_logging("DEBUG")
    setup_logging("DEBUG")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert not isinstance(root.handlers[0], RichHandler)
    assert root.level == logging.DEBUG


def test_pretty_logging_uses_rich():
    setup_logging("INFO", "pretty")

    assert isinstance(logging.getLogger().handlers[0], RichHandler)


def test_sdk_logs_reach_root_handler():
    setup_logging("INFO")

    sdk_logger = logging.getLogger("mosaicolabs.comm")
    assert sdk_logger.getEffectiveLevel() == logging.INFO
    assert sdk_logger.propagate

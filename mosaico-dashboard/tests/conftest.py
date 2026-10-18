import logging

import pytest


@pytest.fixture(autouse=True)
def isolated_from_local_env(tmp_path, monkeypatch):
    """Run every test in an empty directory, so a developer's `.env` is never read."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def restore_root_logger():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)

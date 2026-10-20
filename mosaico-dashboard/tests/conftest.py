import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from mosaico_dashboard.db.tables import metadata


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


@pytest.fixture
def sqlite_engine():
    """In-memory SQLite with the dashboard schema, shared across threads."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata.create_all(engine)
    return engine


@pytest.fixture
def sqlite_file(tmp_path) -> Path:
    """A SQLite file with the dashboard schema, for tests with child processes."""
    path = tmp_path / "dashboard.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    metadata.create_all(engine)
    engine.dispose()
    return path

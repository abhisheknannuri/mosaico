import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from mosaico_dashboard.db.tables import metadata


@pytest.fixture(autouse=True)
def isolated_from_local_env(tmp_path, monkeypatch):
    """Run every test in an empty directory, so a developer's `.env` is never read; the
    web app never starts a real worker."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DASHBOARD_MANAGE_WORKER", "false")


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


class FakeProcesses:
    def __init__(self):
        self.started: list[str] = []

    def is_alive(self, name: str) -> bool:
        return name in self.started

    def start(self, name: str) -> None:
        if name not in self.started:
            self.started.append(name)

    def stop_all(self) -> None:
        self.started.clear()


@pytest.fixture
def fake_processes() -> FakeProcesses:
    return FakeProcesses()

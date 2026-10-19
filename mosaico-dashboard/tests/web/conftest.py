import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from mosaico_dashboard.db.engine import create_db_engine
from mosaico_dashboard.db.tables import metadata
from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings

UNREACHABLE_DATABASE_URL = (
    "postgresql+psycopg://dashboard:dashboard@127.0.0.1:1/dashboard"
)


def memory_engine() -> Engine:
    """In-memory SQLite with the schema, shared across threads (TestClient uses a thread)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata.create_all(engine)
    return engine


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def client(gateway) -> TestClient:
    return TestClient(create_app(Settings(), gateway=gateway, engine=memory_engine()))


@pytest.fixture
def client_daemon_down() -> TestClient:
    app = create_app(
        Settings(), gateway=FakeGateway(available=False), engine=memory_engine()
    )
    return TestClient(app)


@pytest.fixture
def client_database_down() -> TestClient:
    engine = create_db_engine(UNREACHABLE_DATABASE_URL)
    return TestClient(create_app(Settings(), gateway=FakeGateway(), engine=engine))

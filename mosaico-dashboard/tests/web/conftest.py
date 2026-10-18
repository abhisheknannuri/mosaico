import pytest
from fastapi.testclient import TestClient

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def client(gateway) -> TestClient:
    return TestClient(create_app(Settings(), gateway=gateway))

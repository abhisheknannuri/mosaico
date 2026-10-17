import pytest
from fastapi.testclient import TestClient

from mosaico_dashboard.main import create_app
from mosaico_dashboard.settings import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings()))

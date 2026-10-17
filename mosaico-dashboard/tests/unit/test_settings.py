import pytest
from pydantic import ValidationError

from mosaico_dashboard.settings import Settings


@pytest.fixture(autouse=True)
def no_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_defaults():
    settings = Settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.mosaico_host == "localhost"
    assert settings.mosaico_port == 6726
    assert settings.mosaico_api_key is None


def test_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("DASHBOARD_PORT", "9000")
    monkeypatch.setenv("DASHBOARD_MOSAICO_HOST", "mosaicod-server")

    settings = Settings()

    assert settings.port == 9000
    assert settings.mosaico_host == "mosaicod-server"


def test_api_key_is_hidden(monkeypatch):
    monkeypatch.setenv("DASHBOARD_MOSAICO_API_KEY", "msco_secretpayload_1234abcd")

    settings = Settings()

    assert "msco_secretpayload" not in repr(settings)
    assert settings.mosaico_api_key is not None
    assert settings.mosaico_api_key.get_secret_value() == "msco_secretpayload_1234abcd"


def test_invalid_log_format_is_rejected(monkeypatch):
    monkeypatch.setenv("DASHBOARD_LOG_FORMAT", "json")

    with pytest.raises(ValidationError):
        Settings()

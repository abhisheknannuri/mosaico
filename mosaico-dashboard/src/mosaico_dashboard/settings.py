"""Dashboard configuration, read from DASHBOARD_* environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from mosaico_dashboard.logging_config import LogFormat


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DASHBOARD_", env_file=".env")

    # Web server
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: LogFormat = "plain"

    # mosaicod connection
    mosaico_host: str = "localhost"
    mosaico_port: int = 6726
    mosaico_api_key: SecretStr | None = None
    mosaico_tls: bool = False
    mosaico_tls_cert_path: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

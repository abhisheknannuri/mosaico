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

    # Dashboard database
    database_url: str = (
        "postgresql+psycopg://dashboard:dashboard@localhost:5433/dashboard"
    )
    migrate_on_start: bool = True

    # Worker
    worker_poll_seconds: float = 1.0

    # Ingestion: folder on this machine with the ROS bags to ingest, and form defaults
    ingest_dir: Path | None = None
    ingest_ros_distro: str | None = None
    ingest_keep_partial: bool = False

    # mosaicod connection
    mosaico_host: str = "localhost"
    mosaico_port: int = 6726
    mosaico_api_key: SecretStr | None = None
    mosaico_tls: bool = False
    mosaico_tls_cert_path: Path | None = None
    mosaico_connect_timeout: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()

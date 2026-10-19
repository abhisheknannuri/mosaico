"""Build the shared resources (gateway, database engine) from settings."""

from sqlalchemy import Engine

from mosaico_dashboard.db.engine import create_db_engine
from mosaico_dashboard.gateway.sdk import SdkGateway
from mosaico_dashboard.settings import Settings


def build_gateway(settings: Settings) -> SdkGateway:
    api_key = settings.mosaico_api_key
    return SdkGateway(
        host=settings.mosaico_host,
        port=settings.mosaico_port,
        api_key=api_key.get_secret_value() if api_key else None,
        tls=settings.mosaico_tls,
        tls_cert_path=settings.mosaico_tls_cert_path,
        connect_timeout=settings.mosaico_connect_timeout,
    )


def build_engine(settings: Settings) -> Engine:
    return create_db_engine(settings.database_url)

"""Database engine and health check."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

CONNECT_TIMEOUT_SECONDS = 2


def create_db_engine(url: str) -> Engine:
    connect_args = (
        {"connect_timeout": CONNECT_TIMEOUT_SECONDS}
        if url.startswith("postgresql")
        else {}
    )
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def ping(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True

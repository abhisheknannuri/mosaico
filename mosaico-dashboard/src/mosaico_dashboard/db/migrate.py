"""Apply Alembic migrations from code; safe when web and worker start together."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, pool

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_LOCK_ID = 7_202_610


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_to_head(database_url: str) -> None:
    """On Postgres, an advisory lock makes concurrent callers run one after the other."""
    engine = create_engine(database_url, poolclass=pool.NullPool)
    try:
        with engine.begin() as connection:
            if connection.dialect.name == "postgresql":
                connection.exec_driver_sql(
                    f"SELECT pg_advisory_xact_lock({MIGRATION_LOCK_ID})"
                )
            config = alembic_config(database_url)
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()

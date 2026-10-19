"""Alembic environment: online migrations against the configured database."""

from alembic import context
from sqlalchemy import Connection, engine_from_config, pool

from mosaico_dashboard.db.tables import metadata
from mosaico_dashboard.settings import get_settings


def run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


config = context.config
connection = config.attributes.get("connection")
if connection is not None:
    run(connection)
else:
    if not config.get_main_option("sqlalchemy.url"):
        config.set_main_option(
            "sqlalchemy.url", get_settings().database_url.replace("%", "%%")
        )
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as new_connection:
        run(new_connection)

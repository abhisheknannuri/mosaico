"""Repository: settings changed from the UI, one row per key (defaults come from .env)."""

from datetime import datetime, timezone

from sqlalchemy import Connection, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from mosaico_dashboard.db.tables import setting


def get_setting(connection: Connection, key: str) -> str | None:
    return connection.execute(
        select(setting.c.value).where(setting.c.key == key)
    ).scalar_one_or_none()


def set_setting(connection: Connection, key: str, value: str) -> None:
    insert = pg_insert if connection.dialect.name == "postgresql" else sqlite_insert
    values = {"value": value, "updated_at": datetime.now(timezone.utc)}
    statement = insert(setting).values(key=key, **values)
    connection.execute(
        statement.on_conflict_do_update(index_elements=["key"], set_=values)
    )


def delete_setting(connection: Connection, key: str) -> None:
    connection.execute(delete(setting).where(setting.c.key == key))

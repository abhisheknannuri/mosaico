"""Table definitions (SQLAlchemy Core). Portable types, so tests can use SQLite."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

job = Table(
    "job",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("kind", String(40), nullable=False),
    Column("status", String(16), nullable=False, index=True),
    Column("params", JSON, nullable=False),
    Column("progress", JSON),
    Column("error", Text),
    Column("cancel_requested", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
)

worker = Table(
    "worker",
    metadata,
    Column("name", String(40), primary_key=True),
    Column("pid", Integer),
    Column("started_at", DateTime(timezone=True)),
    Column("heartbeat_at", DateTime(timezone=True)),
    Column("stop_requested", Boolean, nullable=False, default=False),
)

setting = Table(
    "setting",
    metadata,
    Column("key", String(60), primary_key=True),
    Column("value", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

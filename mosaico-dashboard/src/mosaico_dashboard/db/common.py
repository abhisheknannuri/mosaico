"""Helpers shared by repositories."""

from datetime import datetime, timezone
from typing import overload


@overload
def utc(value: datetime) -> datetime: ...
@overload
def utc(value: None) -> None: ...
def utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; all stored times are UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)

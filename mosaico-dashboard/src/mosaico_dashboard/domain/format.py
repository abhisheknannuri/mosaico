"""Human-readable formatting of sizes, times and durations."""

from datetime import datetime, timedelta

EMPTY = "—"

_SIZE_UNITS = ["B", "kB", "MB", "GB", "TB", "PB"]


def format_bytes(size: int) -> str:
    """Decimal units: 366185194 -> '366.2 MB'."""
    value = float(size)
    unit = 0
    while value >= 1000 and unit < len(_SIZE_UNITS) - 1:
        value /= 1000
        unit += 1
    if unit == 0:
        return f"{size} B"
    return f"{value:.1f} {_SIZE_UNITS[unit]}"


def format_duration(duration: timedelta | None) -> str:
    """'850 ms', '20.5 s', '12 min 30 s', '2 h 05 min'."""
    if duration is None:
        return EMPTY
    seconds = duration.total_seconds()
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes} min {secs} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def format_datetime(value: datetime | None) -> str:
    """'10 May 2024, 00:27 UTC'."""
    if value is None:
        return EMPTY
    return value.strftime("%d %b %Y, %H:%M UTC")

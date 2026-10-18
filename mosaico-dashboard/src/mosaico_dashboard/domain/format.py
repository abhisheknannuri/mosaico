"""Human-readable formatting of sizes, shares, times and durations."""

from datetime import datetime, timedelta

EMPTY = "—"

_SIZE_UNITS = ["B", "kB", "MB", "GB", "TB", "PB"]


def format_bytes(size: int) -> str:
    """Decimal units, 3 significant digits: '1.98 GB', '366 MB', '14.4 kB'."""
    value = float(size)
    unit = 0
    while value >= 999.5 and unit < len(_SIZE_UNITS) - 1:
        value /= 1000
        unit += 1
    if unit == 0:
        return f"{size} B"
    decimals = 0 if value >= 99.95 else 1 if value >= 9.995 else 2
    return f"{value:.{decimals}f} {_SIZE_UNITS[unit]}"


def format_bytes_exact(size: int) -> str:
    """'1,979,880,035 bytes'."""
    return f"{size:,} bytes"


def format_percent(share: float) -> str:
    """Share between 0 and 1: '99.7%', '<0.1%' for tiny non-zero shares."""
    if 0 < share < 0.0005:
        return "<0.1%"
    return f"{share * 100:.1f}%"


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
    """'3 Sep 2026, 14:30 UTC'."""
    if value is None:
        return EMPTY
    return f"{value.day} {value:%b %Y, %H:%M} UTC"

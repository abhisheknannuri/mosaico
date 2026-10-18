from datetime import datetime, timedelta, timezone

import pytest

from mosaico_dashboard.domain.format import (
    format_bytes,
    format_datetime,
    format_duration,
)


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 B"),
        (999, "999 B"),
        (1000, "1.0 kB"),
        (14383, "14.4 kB"),
        (366185194, "366.2 MB"),
        (2_500_000_000, "2.5 GB"),
        (3 * 10**18, "3000.0 PB"),
    ],
)
def test_format_bytes(size, expected):
    assert format_bytes(size) == expected


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (None, "—"),
        (timedelta(0), "0 ms"),
        (timedelta(milliseconds=850), "850 ms"),
        (timedelta(seconds=20.5), "20.5 s"),
        (timedelta(minutes=12, seconds=30), "12 min 30 s"),
        (timedelta(hours=2, minutes=5), "2 h 05 min"),
    ],
)
def test_format_duration(duration, expected):
    assert format_duration(duration) == expected


def test_format_datetime():
    value = datetime(2024, 5, 10, 0, 27, 24, tzinfo=timezone.utc)

    assert format_datetime(value) == "10 May 2024, 00:27 UTC"
    assert format_datetime(None) == "—"

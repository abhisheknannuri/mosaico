from datetime import datetime, timezone

import pytest

from mosaico_dashboard.gateway.base import GatewayUnavailable
from mosaico_dashboard.gateway.sdk import SdkGateway, _to_datetime


def test_unreachable_daemon_raises_gateway_unavailable():
    gateway = SdkGateway(host="127.0.0.1", port=1, connect_timeout=1)

    with pytest.raises(GatewayUnavailable):
        gateway.list_recordings()


def test_nanoseconds_become_utc_datetime():
    assert _to_datetime(1715300844087876797) == datetime(
        2024, 5, 10, 0, 27, 24, 87877, tzinfo=timezone.utc
    )

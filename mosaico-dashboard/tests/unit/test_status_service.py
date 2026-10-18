from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.status import get_daemon_status


def test_reachable_daemon_reports_version():
    status = get_daemon_status(FakeGateway())

    assert status.reachable
    assert status.version == "0.8.0-dev"


def test_unreachable_daemon_is_reported_not_raised():
    status = get_daemon_status(FakeGateway(available=False))

    assert not status.reachable
    assert status.version is None

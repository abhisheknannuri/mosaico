"""Connection status of mosaicod."""

from mosaico_dashboard.domain.models import DaemonStatus
from mosaico_dashboard.gateway.base import GatewayUnavailable, MosaicoGateway


def get_daemon_status(gateway: MosaicoGateway) -> DaemonStatus:
    try:
        version = gateway.check_connection()
    except GatewayUnavailable:
        return DaemonStatus(reachable=False, version=None)
    return DaemonStatus(reachable=True, version=version)

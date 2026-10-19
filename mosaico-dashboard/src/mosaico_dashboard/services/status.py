"""Connection status of mosaicod and the dashboard database."""

from sqlalchemy import Engine

from mosaico_dashboard.db.engine import ping
from mosaico_dashboard.domain.models import DaemonStatus
from mosaico_dashboard.gateway.base import GatewayUnavailable, MosaicoGateway


def get_daemon_status(gateway: MosaicoGateway) -> DaemonStatus:
    try:
        version = gateway.check_connection()
    except GatewayUnavailable:
        return DaemonStatus(reachable=False, version=None)
    return DaemonStatus(reachable=True, version=version)


def database_reachable(engine: Engine) -> bool:
    return ping(engine)

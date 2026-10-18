"""What the dashboard needs from mosaicod, independent of how it is fetched."""

from typing import Protocol

from mosaico_dashboard.domain.models import Recording, SensorStream


class GatewayError(Exception):
    """Base class for errors raised by a gateway."""


class GatewayUnavailable(GatewayError):
    """mosaicod cannot be reached or did not answer in time."""


class RecordingNotFound(GatewayError):
    """No recording with the given name."""

    def __init__(self, name: str):
        super().__init__(f"Recording '{name}' not found")
        self.name = name


class MosaicoGateway(Protocol):
    def check_connection(self) -> str:
        """Returns the mosaicod version. Raises GatewayUnavailable."""
        ...

    def list_recordings(self) -> list[Recording]: ...

    def get_recording(self, name: str) -> Recording:
        """Raises RecordingNotFound."""
        ...

    def list_streams(self, recording: str) -> list[SensorStream]:
        """Raises RecordingNotFound."""
        ...

    def close(self) -> None: ...

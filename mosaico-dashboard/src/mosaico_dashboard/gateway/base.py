"""What the dashboard needs from mosaicod, independent of how it is fetched."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from mosaico_dashboard.domain.models import (
    BagFile,
    DryRunTopic,
    IngestOutcome,
    IngestRequest,
    Progress,
    Recording,
    SensorStream,
)


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

    def list_bag_files(self, folder: Path) -> list[BagFile]:
        """ROS bags in a local folder, named as the SDK watchdog would name them.

        Raises ValueError if `folder` doesn't exist or isn't a folder.
        """
        ...

    def bag_extensions(self) -> list[str]:
        """File extensions the SDK can ingest (`.mcap`, …)."""
        ...

    def ros_distros(self) -> list[str]:
        """ROS distributions the SDK can parse messages for (`ros2_humble`, …)."""
        ...

    def dry_run(self, request: IngestRequest) -> list[DryRunTopic]:
        """What ingesting the bag would do, per topic, without contacting mosaicod.

        Raises if the bag can't be opened (unreadable, or no topic matches a filter).
        """
        ...

    def ingest(
        self, request: IngestRequest, on_progress: Callable[[Progress], None]
    ) -> IngestOutcome:
        """Ingest a ROS bag as a new recording, reporting progress as it goes.

        Blocks until done; Ctrl-C (SIGINT) ends it as "cancelled". Raises on failure, e.g.
        when the recording already exists.
        """
        ...

    def close(self) -> None: ...

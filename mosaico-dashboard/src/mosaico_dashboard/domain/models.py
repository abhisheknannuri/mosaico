"""Dashboard models: what the pages show, independent of the Mosaico SDK classes."""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DaemonStatus(DomainModel):
    """Whether mosaicod answers, and its version when it does."""

    reachable: bool
    version: str | None


class Upload(DomainModel):
    """One ingestion session: an immutable layer of sensor streams in a recording."""

    id: str
    started_at: datetime
    completed_at: datetime | None
    topics: list[str]

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


class Recording(DomainModel):
    """A Mosaico sequence."""

    name: str
    uploaded_at: datetime
    data_start: datetime | None
    data_end: datetime | None
    size_bytes: int
    metadata: dict[str, Any]
    uploads: list[Upload]

    @property
    def duration(self) -> timedelta | None:
        if self.data_start is None or self.data_end is None:
            return None
        return self.data_end - self.data_start

    @property
    def stream_count(self) -> int:
        return sum(len(upload.topics) for upload in self.uploads)


class RecordingSummary(DomainModel):
    """A recording with the sensor categories of its streams, for list views."""

    recording: Recording
    sensor_categories: list[str]


class SensorStream(DomainModel):
    """A Mosaico topic: one stream of typed messages inside a recording."""

    recording: str
    topic: str
    ontology_tag: str
    ros_type: str | None
    size_bytes: int
    data_start: datetime | None
    data_end: datetime | None

    @property
    def duration(self) -> timedelta | None:
        if self.data_start is None or self.data_end is None:
            return None
        return self.data_end - self.data_start

"""Dashboard models: what the pages show, independent of the Mosaico SDK classes."""

from datetime import datetime, timedelta
from typing import Any, Literal

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
    """A recording with the ontology tags of its streams, for list views."""

    recording: Recording
    ontology_tags: list[str]


class OntologyStorage(DomainModel):
    """Storage used by one ontology tag (e.g. 'IMU') across the catalog."""

    ontology_tag: str
    stream_count: int
    recording_count: int
    size_bytes: int
    share: float


class Overview(DomainModel):
    """Catalog-wide totals for the overview page."""

    recording_count: int
    stream_count: int
    total_bytes: int
    recorded_duration: timedelta
    storage_by_ontology: list[OntologyStorage]
    latest: list[Recording]


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


class TopicProgress(DomainModel):
    """Progress of one topic in an ingestion or export."""

    name: str
    done: int
    total: int | None
    status: str | None


class Progress(DomainModel):
    """Progress of an ingestion or export; `finished` once every message is processed."""

    topics: list[TopicProgress]
    done: int
    total: int
    finished: bool


class IngestRequest(DomainModel):
    """A ROS bag on this machine, to be ingested as one recording."""

    file_path: str
    sequence_name: str
    metadata: dict[str, Any] = {}
    keep_partial: bool = False


IngestOutcome = Literal["completed", "cancelled"]

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]

FINISHED_STATUSES = ("completed", "failed", "cancelled")


class Job(DomainModel):
    """Background work run by the worker, one at a time."""

    id: str
    kind: str
    status: JobStatus
    params: dict[str, Any]
    progress: Progress | None
    error: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @property
    def finished(self) -> bool:
        return self.status in FINISHED_STATUSES

    @property
    def duration(self) -> timedelta | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return self.finished_at - self.started_at

    @property
    def share_done(self) -> float:
        if self.status == "completed":
            return 1.0
        if self.progress is None or not self.progress.total:
            return 0.0
        return self.progress.done / self.progress.total


class BagFile(DomainModel):
    """A ROS bag in the ingest folder; `in_mosaico` is None when mosaicod couldn't be asked."""

    relative_path: str
    path: str
    size_bytes: int
    modified_at: datetime
    recording_name: str
    in_mosaico: bool | None = None


IngestFolderStatus = Literal["not_configured", "missing", "ok"]


class IngestFolder(DomainModel):
    """The configured ingest folder and the bags in it, sorted by path."""

    path: str | None
    status: IngestFolderStatus
    files: list[BagFile]


class DryRunTopic(DomainModel):
    """A topic of a bag, as a real ingestion would handle it."""

    name: str
    accepted: bool
    adapter: str | None = None
    msg_count: int | None = None
    reason: str | None = None


DryRunVerdict = Literal["ok", "warn", "blocked"]


class DryRun(DomainModel):
    """What ingesting a bag would do: ok (every topic), warn (some topics skipped) or
    blocked (an error, or no topic can be ingested)."""

    request: IngestRequest | None
    topics: list[DryRunTopic] = []
    error: str | None = None

    @property
    def accepted(self) -> list[DryRunTopic]:
        return [t for t in self.topics if t.accepted]

    @property
    def rejected(self) -> list[DryRunTopic]:
        return [t for t in self.topics if not t.accepted]

    @property
    def message_count(self) -> int:
        return sum(t.msg_count or 0 for t in self.accepted)

    @property
    def verdict(self) -> DryRunVerdict:
        if self.error or not self.accepted:
            return "blocked"
        return "warn" if self.rejected else "ok"


_NAME_FORBIDDEN = set("!\"'*£$%&. /:")


def recording_name_problem(name: str) -> str | None:
    """Why mosaicod would refuse `name` as a recording (sequence) name, or None."""
    if not name:
        return "Enter a recording name."
    bad = sorted(
        {
            c
            for c in name
            if c in _NAME_FORBIDDEN or not c.isascii() or not c.isprintable()
        }
    )
    if bad:
        shown = " ".join("space" if c == " " else c for c in bad)
        return f"The recording name can't contain: {shown}"
    return None

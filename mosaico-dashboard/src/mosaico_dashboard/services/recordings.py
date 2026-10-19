"""Recordings: list and summaries."""

from datetime import datetime, timezone

from mosaico_dashboard.domain.models import Recording, RecordingSummary
from mosaico_dashboard.gateway.base import MosaicoGateway

_OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def recorded_at(recording: Recording) -> datetime:
    """Sort key: when the data was recorded; recordings without data sort oldest."""
    return recording.data_start or _OLDEST


def list_recording_summaries(gateway: MosaicoGateway) -> list[RecordingSummary]:
    """Newest recorded first; recordings without data last."""
    summaries = [
        RecordingSummary(
            recording=recording,
            ontology_tags=_ontology_tags(gateway, recording),
        )
        for recording in gateway.list_recordings()
    ]
    return sorted(summaries, key=lambda s: recorded_at(s.recording), reverse=True)


def _ontology_tags(gateway: MosaicoGateway, recording: Recording) -> list[str]:
    streams = gateway.list_streams(recording.name)
    return sorted({stream.ontology_tag for stream in streams})

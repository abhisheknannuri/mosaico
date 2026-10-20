"""Catalog-wide totals for the overview page."""

from collections import defaultdict
from datetime import datetime, timedelta

from mosaico_dashboard.domain.models import OntologyStorage, Overview, SensorStream
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.recordings import recorded_at


def get_overview(gateway: MosaicoGateway, latest_count: int = 5) -> Overview:
    recordings = gateway.list_recordings()
    bytes_by_tag: dict[str, int] = defaultdict(int)
    streams_by_tag: dict[str, int] = defaultdict(int)
    recordings_by_tag: dict[str, set[str]] = defaultdict(set)
    recorded = timedelta()
    for recording in recordings:
        streams = gateway.list_streams(recording.name)
        recorded += covered_time(streams)
        for stream in streams:
            bytes_by_tag[stream.ontology_tag] += stream.size_bytes
            streams_by_tag[stream.ontology_tag] += 1
            recordings_by_tag[stream.ontology_tag].add(recording.name)

    total_bytes = sum(r.size_bytes for r in recordings)
    storage = [
        OntologyStorage(
            ontology_tag=tag,
            stream_count=streams_by_tag[tag],
            recording_count=len(recordings_by_tag[tag]),
            size_bytes=size,
            share=size / total_bytes if total_bytes else 0.0,
        )
        for tag, size in sorted(
            bytes_by_tag.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return Overview(
        recording_count=len(recordings),
        stream_count=sum(streams_by_tag.values()),
        total_bytes=total_bytes,
        recorded_duration=recorded,
        storage_by_ontology=storage,
        latest=sorted(recordings, key=recorded_at, reverse=True)[:latest_count],
    )


def covered_time(streams: list[SensorStream]) -> timedelta:
    """Time during which at least one stream has data: overlapping streams count once,
    and gaps (e.g. between bags appended to one recording) don't count."""
    ranges = sorted(
        (s.data_start, s.data_end) for s in streams if s.data_start and s.data_end
    )
    merged: list[list[datetime]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum((end - start for start, end in merged), timedelta())

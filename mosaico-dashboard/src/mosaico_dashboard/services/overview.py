"""Catalog-wide totals for the overview page."""

from collections import defaultdict
from datetime import timedelta

from mosaico_dashboard.domain.models import OntologyStorage, Overview
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.recordings import recorded_at


def get_overview(gateway: MosaicoGateway, latest_count: int = 5) -> Overview:
    recordings = gateway.list_recordings()
    bytes_by_tag: dict[str, int] = defaultdict(int)
    streams_by_tag: dict[str, int] = defaultdict(int)
    recordings_by_tag: dict[str, set[str]] = defaultdict(set)
    for recording in recordings:
        for stream in gateway.list_streams(recording.name):
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
        recorded_duration=sum(
            (r.duration for r in recordings if r.duration), timedelta()
        ),
        storage_by_ontology=storage,
        latest=sorted(recordings, key=recorded_at, reverse=True)[:latest_count],
    )

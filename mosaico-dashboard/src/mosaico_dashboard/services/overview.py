"""Catalog-wide totals for the overview page."""

from collections import defaultdict
from datetime import timedelta

from mosaico_dashboard.domain.models import CategoryStorage, Overview
from mosaico_dashboard.domain.vocabulary import sensor_type
from mosaico_dashboard.gateway.base import MosaicoGateway
from mosaico_dashboard.services.recordings import recorded_at


def get_overview(gateway: MosaicoGateway, latest_count: int = 5) -> Overview:
    recordings = gateway.list_recordings()
    bytes_by_category: dict[str, int] = defaultdict(int)
    stream_count = 0
    for recording in recordings:
        for stream in gateway.list_streams(recording.name):
            category = sensor_type(stream.ontology_tag).category
            bytes_by_category[category] += stream.size_bytes
            stream_count += 1

    total_bytes = sum(r.size_bytes for r in recordings)
    storage = [
        CategoryStorage(
            category=category,
            size_bytes=size,
            share=size / total_bytes if total_bytes else 0.0,
        )
        for category, size in sorted(
            bytes_by_category.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return Overview(
        recording_count=len(recordings),
        stream_count=stream_count,
        total_bytes=total_bytes,
        recorded_duration=sum(
            (r.duration for r in recordings if r.duration), timedelta()
        ),
        storage_by_category=storage,
        latest=sorted(recordings, key=recorded_at, reverse=True)[:latest_count],
    )

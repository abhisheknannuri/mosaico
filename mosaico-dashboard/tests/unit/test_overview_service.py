from datetime import timedelta

import pytest

from mosaico_dashboard.gateway.fake import FakeGateway, sample_streams
from mosaico_dashboard.services.overview import get_overview


def test_totals():
    overview = get_overview(FakeGateway())

    assert overview.recording_count == 2
    assert overview.stream_count == 9
    assert overview.total_bytes == 180_230_000 + 598_200_000
    assert overview.recorded_duration == timedelta(seconds=20.5 + 14.5)


def test_storage_by_ontology_is_sorted_and_sums_to_one():
    storage = get_overview(FakeGateway()).storage_by_ontology

    assert [s.ontology_tag for s in storage[:2]] == ["Image", "CompressedImage"]
    assert [s.size_bytes for s in storage] == sorted(
        (s.size_bytes for s in storage), reverse=True
    )
    assert sum(s.share for s in storage) == pytest.approx(1.0)


def test_storage_counts_streams_and_recordings_per_tag():
    streams = sample_streams()
    second_imu = streams[0].model_copy(update={"recording": "r2b_robotarm_0"})
    gateway = FakeGateway(streams=[*streams, second_imu])

    imu = next(
        s for s in get_overview(gateway).storage_by_ontology if s.ontology_tag == "IMU"
    )

    assert (imu.stream_count, imu.recording_count) == (2, 2)
    assert imu.size_bytes == 2 * streams[0].size_bytes


def test_latest_is_newest_recorded_first_and_limited():
    overview = get_overview(FakeGateway(), latest_count=1)

    assert len(overview.latest) == 1


def test_empty_catalog():
    overview = get_overview(FakeGateway(recordings=[], streams=[]))

    assert overview.recording_count == 0
    assert overview.storage_by_ontology == []
    assert overview.latest == []

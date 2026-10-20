from datetime import datetime, timedelta, timezone

import pytest

from mosaico_dashboard.gateway.fake import FakeGateway, sample_streams
from mosaico_dashboard.services.overview import covered_time, get_overview


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


T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def stream_between(start_s: float, end_s: float):
    return sample_streams()[0].model_copy(
        update={
            "data_start": T0 + timedelta(seconds=start_s),
            "data_end": T0 + timedelta(seconds=end_s),
        }
    )


def test_covered_time_counts_overlapping_streams_once():
    streams = [stream_between(0, 60), stream_between(30, 90), stream_between(10, 20)]

    assert covered_time(streams) == timedelta(seconds=90)


def test_covered_time_skips_the_gap_between_appended_bags():
    nine_days = 9 * 24 * 3600
    streams = [stream_between(0, 60), stream_between(nine_days, nine_days + 90)]

    assert covered_time(streams) == timedelta(seconds=150)


def test_covered_time_ignores_streams_without_data():
    empty = stream_between(0, 1).model_copy(
        update={"data_start": None, "data_end": None}
    )

    assert covered_time([empty]) == timedelta()

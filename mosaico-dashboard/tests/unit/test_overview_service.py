from datetime import timedelta

import pytest

from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.overview import get_overview


def test_totals():
    overview = get_overview(FakeGateway())

    assert overview.recording_count == 2
    assert overview.stream_count == 9
    assert overview.total_bytes == 180_230_000 + 598_200_000
    assert overview.recorded_duration == timedelta(seconds=20.5 + 14.5)


def test_storage_by_category_is_sorted_and_sums_to_one():
    storage = get_overview(FakeGateway()).storage_by_category

    assert storage[0].category == "Camera"
    assert [s.size_bytes for s in storage] == sorted(
        (s.size_bytes for s in storage), reverse=True
    )
    assert sum(s.share for s in storage) == pytest.approx(1.0)


def test_latest_is_newest_recorded_first_and_limited():
    overview = get_overview(FakeGateway(), latest_count=1)

    assert len(overview.latest) == 1


def test_empty_catalog():
    overview = get_overview(FakeGateway(recordings=[], streams=[]))

    assert overview.recording_count == 0
    assert overview.storage_by_category == []
    assert overview.latest == []

import pytest

from mosaico_dashboard.gateway.base import (
    GatewayUnavailable,
    MosaicoGateway,
    RecordingNotFound,
)
from mosaico_dashboard.gateway.fake import FakeGateway


@pytest.fixture
def gateway() -> MosaicoGateway:
    return FakeGateway()


def test_lists_sample_recordings(gateway):
    names = [r.name for r in gateway.list_recordings()]

    assert names == ["r2b_galileo2_0", "r2b_robotarm_0"]


def test_get_recording(gateway):
    recording = gateway.get_recording("r2b_robotarm_0")

    assert recording.stream_count == 2
    assert recording.size_bytes == 598_200_000


def test_unknown_recording_raises(gateway):
    with pytest.raises(RecordingNotFound) as error:
        gateway.get_recording("missing")

    assert error.value.name == "missing"


def test_list_streams_of_one_recording(gateway):
    streams = gateway.list_streams("r2b_galileo2_0")

    assert len(streams) == 7
    assert {s.recording for s in streams} == {"r2b_galileo2_0"}


def test_list_streams_of_unknown_recording_raises(gateway):
    with pytest.raises(RecordingNotFound):
        gateway.list_streams("missing")


def test_custom_data_replaces_samples():
    assert FakeGateway(recordings=[], streams=[]).list_recordings() == []


def test_unavailable_fake_raises():
    gateway = FakeGateway(available=False)

    with pytest.raises(GatewayUnavailable):
        gateway.check_connection()
    with pytest.raises(GatewayUnavailable):
        gateway.list_recordings()

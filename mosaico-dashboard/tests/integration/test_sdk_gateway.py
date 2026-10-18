from concurrent.futures import ThreadPoolExecutor

import pytest

from mosaico_dashboard.gateway.base import GatewayUnavailable, RecordingNotFound
from mosaico_dashboard.gateway.sdk import SdkGateway

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def gateway():
    gateway = SdkGateway(host="localhost", port=6726, connect_timeout=1)
    try:
        recordings = gateway.list_recordings()
    except GatewayUnavailable:
        pytest.skip("mosaicod is not running on localhost:6726")
    if not recordings:
        pytest.skip("mosaicod has no recordings")
    yield gateway
    gateway.close()


@pytest.fixture(scope="module")
def recording_name(gateway) -> str:
    return gateway.list_recordings()[0].name


def test_recordings_are_mapped(gateway):
    for recording in gateway.list_recordings():
        assert recording.uploaded_at.tzinfo is not None
        assert recording.size_bytes > 0
        assert recording.stream_count > 0
        if recording.data_start and recording.data_end:
            assert recording.data_start <= recording.data_end


def test_streams_match_recording(gateway, recording_name):
    recording = gateway.get_recording(recording_name)
    streams = gateway.list_streams(recording_name)

    assert len(streams) == recording.stream_count
    assert sum(s.size_bytes for s in streams) == recording.size_bytes
    assert all(s.ontology_tag for s in streams)


def test_ros_type_is_read_from_ros_metadata(gateway, recording_name):
    streams = gateway.list_streams(recording_name)

    assert any(s.ros_type and "/msg/" in s.ros_type for s in streams)


def test_unknown_recording_raises_not_found(gateway):
    with pytest.raises(RecordingNotFound):
        gateway.get_recording("does_not_exist")
    with pytest.raises(RecordingNotFound):
        gateway.list_streams("does_not_exist")


def test_shared_client_is_safe_across_threads(gateway, recording_name):
    expected = gateway.list_streams(recording_name)

    with ThreadPoolExecutor(max_workers=40) as pool:
        results = list(
            pool.map(lambda _: gateway.list_streams(recording_name), range(200))
        )

    assert all(result == expected for result in results)

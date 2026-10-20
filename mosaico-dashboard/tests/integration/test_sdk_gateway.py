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
        assert recording.size_bytes >= 0
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


def test_check_connection_returns_version(gateway):
    assert gateway.check_connection()


def test_dry_run_of_a_demo_bag_and_logging_is_handed_back(gateway):
    import logging
    from pathlib import Path

    from mosaico_dashboard.domain.models import IngestRequest

    bag = (
        Path(__file__).parents[2]
        / "demo-data/demo_warehouse_run_01/demo_warehouse_run_01.mcap"
    )
    if not bag.exists():
        pytest.skip("demo bags not generated (scripts/make_demo_bags.py)")

    topics = gateway.dry_run(IngestRequest(file_path=str(bag), sequence_name="x"))

    assert {t.name for t in topics if t.accepted} >= {"/imu/data", "/gps/fix"}
    assert all(t.msg_count for t in topics if t.accepted)
    sdk_logger = logging.getLogger("mosaicolabs")
    assert sdk_logger.handlers == [] and sdk_logger.propagate is True


def test_ingestion_deletes_partial_data_unless_kept(gateway):
    from mosaicolabs.enum import SessionLevelErrorPolicy

    from mosaico_dashboard.domain.models import IngestRequest

    request = IngestRequest(file_path="/bags/a.mcap", sequence_name="a")

    assert gateway._injection_config(request).on_error == SessionLevelErrorPolicy.Delete
    kept = request.model_copy(update={"keep_partial": True})
    assert gateway._injection_config(kept).on_error == SessionLevelErrorPolicy.Report


def test_ingestion_options_reach_the_sdk_config(gateway):
    from rosbags.typesys import Stores

    from mosaico_dashboard.domain.models import IngestRequest

    request = IngestRequest(
        file_path="/bags/a.mcap",
        sequence_name="a",
        ros_distro="ros2_humble",
        update_if_exists=True,
        topics=["/imu"],
    )

    config = gateway._injection_config(request)

    assert config.ros_distro == Stores.ROS2_HUMBLE
    assert config.update_if_exists is True
    assert config.topics == ["/imu"]
    assert (
        "ros2_humble" in gateway.ros_distros() and "empty" not in gateway.ros_distros()
    )

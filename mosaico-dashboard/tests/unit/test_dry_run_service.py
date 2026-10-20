from datetime import datetime, timezone

import pytest

from mosaico_dashboard.domain.models import BagFile
from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.ingestion import dry_run_ingestion, metadata_from_rows

FILE = BagFile(
    relative_path="run_01/drive.mcap",
    path="/bags/run_01/drive.mcap",
    size_bytes=10,
    modified_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    recording_name="run_01-drive__mcap",
)


def test_metadata_rows_skip_empty_keys_and_strip():
    rows = metadata_from_rows([" project ", "", "robot"], [" wh ", "x", "carter"])

    assert rows == {"project": "wh", "robot": "carter"}


def test_metadata_duplicate_key():
    with pytest.raises(ValueError, match="'robot' is used twice"):
        metadata_from_rows(["robot", "robot"], ["a", "b"])


def test_dry_run_builds_the_request():
    result = dry_run_ingestion(
        FakeGateway(), FILE, " my_run ", ["project"], ["warehouse"]
    )

    assert result.request is not None
    assert result.request.file_path == "/bags/run_01/drive.mcap"
    assert result.request.sequence_name == "my_run"
    assert result.request.metadata == {"project": "warehouse"}
    assert result.verdict == "warn"


def test_invalid_name_is_reported_without_a_dry_run():
    result = dry_run_ingestion(FakeGateway(), FILE, "my run", [], [])

    assert result.request is None
    assert result.error is not None and "space" in result.error


def test_duplicate_metadata_is_reported():
    result = dry_run_ingestion(FakeGateway(), FILE, "ok", ["a", "a"], ["1", "2"])

    assert result.error == "The metadata key 'a' is used twice."


def test_sdk_errors_are_reported():
    class Unreadable(FakeGateway):
        def dry_run(self, request):
            raise RuntimeError("Unable to initialize ROSLoader")

    result = dry_run_ingestion(Unreadable(), FILE, "ok", [], [])

    assert result.verdict == "blocked"
    assert result.error == "Unable to initialize ROSLoader"


def test_options_go_into_the_request():
    from mosaico_dashboard.domain.models import IngestOptions

    options = IngestOptions(
        ros_distro="ros2_humble",
        keep_partial=True,
        update_if_exists=True,
        topics=["/imu/data", "/robot/custom"],
    )

    result = dry_run_ingestion(FakeGateway(), FILE, "run", [], [], options)

    assert result.request is not None
    assert result.request.ros_distro == "ros2_humble"
    assert result.request.keep_partial and result.request.update_if_exists
    assert result.request.topics == ["/imu/data", "/robot/custom"]
    assert [t.name for t in result.filtered] == ["/gps/fix"]
    assert [t.name for t in result.rejected] == ["/robot/custom"]


def test_unknown_ros_distro():
    from mosaico_dashboard.domain.models import IngestOptions

    result = dry_run_ingestion(
        FakeGateway(), FILE, "run", [], [], IngestOptions(ros_distro="ros9")
    )

    assert result.error == "Unknown ROS distribution 'ros9'."


def test_no_topic_selected():
    from mosaico_dashboard.domain.models import IngestOptions

    result = dry_run_ingestion(
        FakeGateway(), FILE, "run", [], [], IngestOptions(topics=[])
    )

    assert result.error == "Select at least one topic to ingest."


def appending(topics):
    from mosaico_dashboard.domain.models import DryRunTopic

    return FakeGateway(
        dry_run_topics=[
            DryRunTopic(name=name, accepted=True, adapter="A", msg_count=1)
            for name in topics
        ]
    )


def test_appending_skips_topics_the_recording_already_has():
    from mosaico_dashboard.domain.models import IngestOptions
    from mosaico_dashboard.services.ingestion import ALREADY_IN_RECORDING

    result = dry_run_ingestion(
        appending(["/chassis/imu", "/new"]),
        FILE,
        "r2b_galileo2_0",
        [],
        [],
        IngestOptions(update_if_exists=True),
    )

    assert result.verdict == "warn"
    assert [(t.name, t.reason) for t in result.rejected] == [
        ("/chassis/imu", ALREADY_IN_RECORDING)
    ]
    assert result.request is not None and result.request.topics == ["/new"]


def test_appending_only_existing_topics_is_blocked():
    from mosaico_dashboard.domain.models import IngestOptions

    result = dry_run_ingestion(
        appending(["/chassis/imu"]),
        FILE,
        "r2b_galileo2_0",
        [],
        [],
        IngestOptions(update_if_exists=True),
    )

    assert result.verdict == "blocked"


def test_appending_to_a_new_name_changes_nothing():
    from mosaico_dashboard.domain.models import IngestOptions

    result = dry_run_ingestion(
        appending(["/chassis/imu"]),
        FILE,
        "brand_new",
        [],
        [],
        IngestOptions(update_if_exists=True),
    )

    assert result.verdict == "ok"
    assert result.request is not None and result.request.topics is None


def test_appending_needs_mosaicod():
    from mosaico_dashboard.domain.models import IngestOptions

    result = dry_run_ingestion(
        FakeGateway(available=False),
        FILE,
        "r2b_galileo2_0",
        [],
        [],
        IngestOptions(update_if_exists=True),
    )

    assert result.error is not None and "can't be checked" in result.error

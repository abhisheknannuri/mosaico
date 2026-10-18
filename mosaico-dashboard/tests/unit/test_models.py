from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from mosaico_dashboard.domain.models import Recording, SensorStream, Upload

T0 = datetime(2024, 5, 10, 0, 27, 24, tzinfo=timezone.utc)


def make_upload(topics: list[str], completed: bool = True) -> Upload:
    return Upload(
        id="r2b_galileo2_0:01M52PX2V3TS2JARZZTP0FFKVJ",
        started_at=T0,
        completed_at=T0 + timedelta(seconds=25) if completed else None,
        topics=topics,
    )


def make_recording(**overrides) -> Recording:
    fields = {
        "name": "r2b_galileo2_0",
        "uploaded_at": T0 + timedelta(days=900),
        "data_start": T0,
        "data_end": T0 + timedelta(seconds=20.5),
        "size_bytes": 366185194,
        "metadata": {"ingested_via": "mosaico_example_ros_injection"},
        "uploads": [make_upload(["/chassis/imu", "/tf"]), make_upload(["/labels"])],
    }
    return Recording(**(fields | overrides))


def test_recording_duration_and_stream_count():
    recording = make_recording()

    assert recording.duration == timedelta(seconds=20.5)
    assert recording.stream_count == 3


def test_recording_without_data_has_no_duration():
    assert make_recording(data_start=None, data_end=None).duration is None


def test_upload_completion():
    assert make_upload([]).is_complete
    assert not make_upload([], completed=False).is_complete


def test_sensor_stream_duration():
    stream = SensorStream(
        recording="r2b_galileo2_0",
        topic="/chassis/imu",
        ontology_tag="IMU",
        ros_type="sensor_msgs/msg/Imu",
        size_bytes=40_000,
        data_start=T0,
        data_end=T0 + timedelta(seconds=21.97),
    )

    assert stream.duration == timedelta(seconds=21.97)


def test_models_are_immutable():
    recording = make_recording()

    with pytest.raises(ValidationError):
        recording.name = "renamed"  # type: ignore[misc]


def test_models_reject_wrong_types():
    with pytest.raises(ValidationError):
        make_recording(size_bytes="large")

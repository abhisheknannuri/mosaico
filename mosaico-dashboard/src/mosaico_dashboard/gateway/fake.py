"""In-memory gateway for tests and UI work without mosaicod."""

from datetime import datetime, timedelta, timezone

from mosaico_dashboard.domain.models import Recording, SensorStream, Upload
from mosaico_dashboard.gateway.base import MosaicoGateway, RecordingNotFound


class FakeGateway(MosaicoGateway):
    def __init__(
        self,
        recordings: list[Recording] | None = None,
        streams: list[SensorStream] | None = None,
    ):
        self._streams = sample_streams() if streams is None else streams
        self._recordings = (
            sample_recordings(self._streams) if recordings is None else recordings
        )

    def list_recordings(self) -> list[Recording]:
        return list(self._recordings)

    def get_recording(self, name: str) -> Recording:
        for recording in self._recordings:
            if recording.name == name:
                return recording
        raise RecordingNotFound(name)

    def list_streams(self, recording: str) -> list[SensorStream]:
        self.get_recording(recording)
        return [s for s in self._streams if s.recording == recording]

    def close(self) -> None:
        pass


RECORDED_AT = datetime(2024, 5, 10, 0, 27, 24, tzinfo=timezone.utc)
UPLOADED_AT = datetime(2026, 10, 15, 9, 30, 0, tzinfo=timezone.utc)


def _stream(
    recording: str, topic: str, tag: str, ros_type: str, size_bytes: int, seconds: float
) -> SensorStream:
    return SensorStream(
        recording=recording,
        topic=topic,
        ontology_tag=tag,
        ros_type=ros_type,
        size_bytes=size_bytes,
        data_start=RECORDED_AT,
        data_end=RECORDED_AT + timedelta(seconds=seconds),
    )


def sample_streams() -> list[SensorStream]:
    galileo = "r2b_galileo2_0"
    robotarm = "r2b_robotarm_0"
    return [
        _stream(galileo, "/chassis/imu", "IMU", "sensor_msgs/msg/Imu", 40_000, 20.5),
        _stream(galileo, "/chassis/odom", "MotionState", "nav_msgs/msg/Odometry", 70_000, 20.5),
        _stream(galileo, "/chassis/battery_state", "BatteryState", "sensor_msgs/msg/BatteryState", 10_000, 20.0),
        _stream(galileo, "/front_stereo_camera/left/image_compressed", "CompressedImage", "sensor_msgs/msg/CompressedImage", 180_000_000, 12.0),
        _stream(galileo, "/front_stereo_camera/left/camera_info", "CameraInfo", "sensor_msgs/msg/CameraInfo", 30_000, 13.7),
        _stream(galileo, "/tf", "FrameTransform", "tf2_msgs/msg/TFMessage", 60_000, 13.7),
        _stream(galileo, "/chassis/ticks", "EncoderTicks", "isaac_ros_nova_interfaces/msg/EncoderTicks", 20_000, 20.5),
        _stream(robotarm, "/joint_states", "RobotJoint", "sensor_msgs/msg/JointState", 200_000, 14.5),
        _stream(robotarm, "/camera/color/image_raw", "Image", "sensor_msgs/msg/Image", 598_000_000, 14.5),
    ]  # fmt: skip


def sample_recordings(streams: list[SensorStream]) -> list[Recording]:
    names = list(dict.fromkeys(s.recording for s in streams))
    recordings = []
    for index, name in enumerate(names):
        own = [s for s in streams if s.recording == name]
        uploaded_at = UPLOADED_AT + timedelta(hours=index)
        upload = Upload(
            id=f"{name}:01M52PX2V3TS2JARZZTP0FFKV{index}",
            started_at=uploaded_at,
            completed_at=uploaded_at + timedelta(seconds=25),
            topics=[s.topic for s in own],
        )
        recordings.append(
            Recording(
                name=name,
                uploaded_at=uploaded_at,
                data_start=min(s.data_start for s in own if s.data_start),
                data_end=max(s.data_end for s in own if s.data_end),
                size_bytes=sum(s.size_bytes for s in own),
                metadata={"source_file": f"{name}.mcap"},
                uploads=[upload],
            )
        )
    return recordings

"""Plain-language names for Mosaico ontology tags."""

from pydantic import BaseModel, ConfigDict

CAMERA = "Camera"
MOTION = "Motion"
POSITION = "Position"
ROBOT = "Robot state"
RANGE = "Range"
ENVIRONMENT = "Environment"
TRANSFORM = "Transform"
DATA = "Data"
OTHER = "Other"


class SensorType(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    category: str


_SENSOR_TYPES: dict[str, tuple[str, str]] = {
    "Image": ("Camera image", CAMERA),
    "CompressedImage": ("Camera image (compressed)", CAMERA),
    "CameraInfo": ("Camera calibration", CAMERA),
    "StereoCamera": ("Stereo camera", CAMERA),
    "RGBDCamera": ("Depth camera (RGB-D)", CAMERA),
    "ToFCamera": ("Depth camera (ToF)", CAMERA),
    "IMU": ("Motion sensor (IMU)", MOTION),
    "Acceleration": ("Acceleration", MOTION),
    "Velocity": ("Velocity", MOTION),
    "MotionState": ("Odometry", MOTION),
    "GPS": ("GPS position", POSITION),
    "GPSStatus": ("GPS status", POSITION),
    "NMEASentence": ("GPS (NMEA)", POSITION),
    "Pose": ("Pose", POSITION),
    "RobotPath": ("Planned path", POSITION),
    "BatteryState": ("Battery", ROBOT),
    "RobotJoint": ("Joint states", ROBOT),
    "Joy": ("Joystick", ROBOT),
    "ForceTorque": ("Force / torque", ROBOT),
    "Lidar": ("Lidar", RANGE),
    "PointCloud2": ("Point cloud", RANGE),
    "LaserScan": ("Laser scan", RANGE),
    "MultiEchoLaserScan": ("Laser scan (multi-echo)", RANGE),
    "Radar": ("Radar", RANGE),
    "Range": ("Distance sensor", RANGE),
    "OccupancyGrid": ("Occupancy map", RANGE),
    "Temperature": ("Temperature", ENVIRONMENT),
    "Pressure": ("Pressure", ENVIRONMENT),
    "Magnetometer": ("Magnetometer", ENVIRONMENT),
    "FrameTransform": ("Coordinate frames", TRANSFORM),
    "Transform": ("Coordinate frame", TRANSFORM),
    "String": ("Text", DATA),
    "Boolean": ("Flag", DATA),
}


def sensor_type(ontology_tag: str) -> SensorType:
    """Unknown or custom tags keep their own name, in the 'Other' category."""
    label, category = _SENSOR_TYPES.get(ontology_tag, (ontology_tag, OTHER))
    return SensorType(label=label, category=category)

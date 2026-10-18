"""Generate small, deterministic ROS 2 demo bags (.mcap).

Usage (from mosaico-dashboard/): poetry run python scripts/make_demo_bags.py [output_dir]
"""

import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from rosbags.rosbag2 import StoragePlugin, Writer
from rosbags.typesys import Stores, get_typestore

TYPESTORE = get_typestore(Stores.ROS2_HUMBLE)
T = TYPESTORE.types

IMU = "sensor_msgs/msg/Imu"
GPS = "sensor_msgs/msg/NavSatFix"
ODOM = "nav_msgs/msg/Odometry"
IMAGE = "sensor_msgs/msg/Image"
BATTERY = "sensor_msgs/msg/BatteryState"
TEMPERATURE = "sensor_msgs/msg/Temperature"

RATES_HZ = {IMU: 200, GPS: 10, ODOM: 50, IMAGE: 5, BATTERY: 1, TEMPERATURE: 1}
TOPICS = {
    IMU: "/imu/data",
    GPS: "/gps/fix",
    ODOM: "/odom",
    IMAGE: "/camera/image_raw",
    BATTERY: "/battery_state",
    TEMPERATURE: "/environment/temperature",
}
ORIGIN_LAT, ORIGIN_LON = 44.6983, 10.6312


@dataclass
class DemoBag:
    name: str
    start: datetime
    seconds: int
    msgtypes: list[str]
    metadata: dict
    gps_gap: tuple[float, float] | None = None
    seed: int = field(default=0)


BAGS = [
    DemoBag(
        name="demo_warehouse_run_01",
        start=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
        seconds=60,
        msgtypes=[IMU, GPS, ODOM, IMAGE, BATTERY],
        metadata={"project": "warehouse-mapping", "site": "Reggio Emilia DC", "robot": "carter-01"},
        seed=1,
    ),
    DemoBag(
        name="demo_warehouse_run_02",
        start=datetime(2026, 9, 3, 14, 30, tzinfo=timezone.utc),
        seconds=60,
        msgtypes=[IMU, GPS, ODOM, BATTERY],
        metadata={"project": "warehouse-mapping", "site": "Reggio Emilia DC", "robot": "carter-02"},
        gps_gap=(20.0, 35.0),
        seed=2,
    ),
    DemoBag(
        name="demo_field_test_01",
        start=datetime(2026, 9, 10, 10, 15, tzinfo=timezone.utc),
        seconds=90,
        msgtypes=[IMU, GPS, TEMPERATURE],
        metadata={"project": "outdoor-field-test", "site": "Modena test track", "robot": "rover-01"},
        seed=3,
    ),
]  # fmt: skip


def header(t_ns: int, frame_id: str):
    stamp = T["builtin_interfaces/msg/Time"](sec=t_ns // 10**9, nanosec=t_ns % 10**9)
    return T["std_msgs/msg/Header"](stamp=stamp, frame_id=frame_id)


def vector3(x: float, y: float, z: float):
    return T["geometry_msgs/msg/Vector3"](x=x, y=y, z=z)


def identity_quaternion():
    return T["geometry_msgs/msg/Quaternion"](x=0.0, y=0.0, z=0.0, w=1.0)


def imu(t_ns: int, s: float, rng: np.random.Generator):
    noise = rng.normal(0, 0.05, 6)
    return T[IMU](
        header=header(t_ns, "imu_link"),
        orientation=identity_quaternion(),
        orientation_covariance=np.zeros(9),
        angular_velocity=vector3(
            noise[0], noise[1], 0.3 * math.sin(0.2 * s) + noise[2]
        ),
        angular_velocity_covariance=np.zeros(9),
        linear_acceleration=vector3(
            0.5 * math.sin(0.5 * s) + noise[3], noise[4], 9.81 + noise[5]
        ),
        linear_acceleration_covariance=np.zeros(9),
    )


def gps(t_ns: int, s: float, rng: np.random.Generator):
    status = T["sensor_msgs/msg/NavSatStatus"](status=0, service=1)
    return T[GPS](
        header=header(t_ns, "gps_link"),
        status=status,
        latitude=ORIGIN_LAT + 0.00002 * s + rng.normal(0, 0.000002),
        longitude=ORIGIN_LON + 0.00003 * s + rng.normal(0, 0.000002),
        altitude=58.0 + rng.normal(0, 0.2),
        position_covariance=np.zeros(9),
        position_covariance_type=0,
    )


def odometry(t_ns: int, s: float, rng: np.random.Generator):
    position = T["geometry_msgs/msg/Point"](x=1.2 * s, y=2.0 * math.sin(0.1 * s), z=0.0)
    pose = T["geometry_msgs/msg/Pose"](
        position=position, orientation=identity_quaternion()
    )
    twist = T["geometry_msgs/msg/Twist"](
        linear=vector3(1.2 + rng.normal(0, 0.02), 0.0, 0.0),
        angular=vector3(0.0, 0.0, 0.3 * math.sin(0.2 * s)),
    )
    return T[ODOM](
        header=header(t_ns, "odom"),
        child_frame_id="base_link",
        pose=T["geometry_msgs/msg/PoseWithCovariance"](
            pose=pose, covariance=np.zeros(36)
        ),
        twist=T["geometry_msgs/msg/TwistWithCovariance"](
            twist=twist, covariance=np.zeros(36)
        ),
    )


def image(t_ns: int, s: float, rng: np.random.Generator):
    height, width = 48, 64
    x = np.linspace(0, 255, width, dtype=np.float32)
    row = (x + 40 * s) % 256
    pixels = np.stack([np.tile(row, (height, 1))] * 3, axis=-1).astype(np.uint8)
    return T[IMAGE](
        header=header(t_ns, "camera_link"),
        height=height,
        width=width,
        encoding="rgb8",
        is_bigendian=0,
        step=width * 3,
        data=pixels.reshape(-1),
    )


def battery(t_ns: int, s: float, rng: np.random.Generator):
    return T[BATTERY](
        header=header(t_ns, "base_link"),
        voltage=25.2 - 0.002 * s,
        temperature=31.0,
        current=-4.2 + rng.normal(0, 0.1),
        charge=float("nan"),
        capacity=float("nan"),
        design_capacity=20.0,
        percentage=0.95 - 0.0008 * s,
        power_supply_status=2,
        power_supply_health=1,
        power_supply_technology=2,
        present=True,
        cell_voltage=np.array([], dtype=np.float32),
        cell_temperature=np.array([], dtype=np.float32),
        location="base",
        serial_number="BAT-0001",
    )


def temperature(t_ns: int, s: float, rng: np.random.Generator):
    return T[TEMPERATURE](
        header=header(t_ns, "base_link"),
        temperature=18.0 + 3.0 * math.sin(s / 30) + rng.normal(0, 0.1),
        variance=0.01,
    )


MAKERS = {
    IMU: imu,
    GPS: gps,
    ODOM: odometry,
    IMAGE: image,
    BATTERY: battery,
    TEMPERATURE: temperature,
}


def write_bag(bag: DemoBag, output_dir: Path) -> Path:
    bag_dir = output_dir / bag.name
    rng = np.random.default_rng(bag.seed)
    start_ns = int(bag.start.timestamp() * 10**9)
    with Writer(bag_dir, version=9, storage_plugin=StoragePlugin.MCAP) as writer:
        connections = {
            msgtype: writer.add_connection(
                TOPICS[msgtype], msgtype, typestore=TYPESTORE
            )
            for msgtype in bag.msgtypes
        }
        messages = []
        for msgtype in bag.msgtypes:
            rate = RATES_HZ[msgtype]
            for i in range(bag.seconds * rate):
                s = i / rate
                if (
                    msgtype == GPS
                    and bag.gps_gap
                    and bag.gps_gap[0] <= s < bag.gps_gap[1]
                ):
                    continue
                messages.append((start_ns + round(s * 10**9), msgtype, s))
        for t_ns, msgtype, s in sorted(messages):
            msg = MAKERS[msgtype](t_ns, s, rng)
            writer.write(
                connections[msgtype], t_ns, TYPESTORE.serialize_cdr(msg, msgtype)
            )
    return bag_dir / f"{bag.name}.mcap"


def main() -> None:
    output_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "demo-data")
    output_dir.mkdir(parents=True, exist_ok=True)
    for bag in BAGS:
        if (output_dir / bag.name).exists():
            print(f"exists, skipped: {output_dir / bag.name}")
            continue
        path = write_bag(bag, output_dir)
        print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

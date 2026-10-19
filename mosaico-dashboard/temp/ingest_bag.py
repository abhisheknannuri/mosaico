"""Ingest one ROS bag into mosaicod with the SDK RosbagInjector.

Run from mosaico-dashboard/: poetry run python temp/ingest_bag.py
"""

from pathlib import Path

from mosaicolabs.bridges.ros import RosbagInjector, ROSInjectionConfig
from mosaicolabs.examples.bridges.helpers import download_asset
from mosaicolabs.examples.config import ASSET_DIR
from rich.console import Console

BAG_URL = (
    "https://api.ngc.nvidia.com/v2/resources/org/nvidia/team/isaac/r2bdataset2024/1/files"
    "?redirect=true&path=r2b_galileo2/r2b_galileo2_0.mcap"
)
MCAP_PATH = Path(ASSET_DIR) / "r2b_galileo2_0.mcap"
SEQUENCE_NAME = "r2b_galileo2_0_ingest_test"


def main() -> None:
    download_asset(BAG_URL, MCAP_PATH.parent, Console(), MCAP_PATH.name)

    config = ROSInjectionConfig(
        file_path=MCAP_PATH,
        sequence_name=SEQUENCE_NAME,
        metadata={"ingested_via": "mosaico-dashboard temp/ingest_bag.py"},
        host="localhost",
        port=6726,
    )
    RosbagInjector(config).run()


if __name__ == "__main__":
    main()

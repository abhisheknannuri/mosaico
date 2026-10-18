"""Ingest the demo ROS bags that mosaicod doesn't have yet (bags are generated if missing).

Usage (from mosaico-dashboard/, with mosaicod running): poetry run python scripts/seed_demo.py
"""

from pathlib import Path

from make_demo_bags import BAGS, write_bag
from mosaicolabs import MosaicoClient
from mosaicolabs.bridges.ros import RosbagInjector, ROSInjectionConfig

OUTPUT_DIR = Path("demo-data")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with MosaicoClient.connect("localhost", 6726) as client:
        existing = set(client.list_sequences())

    for bag in BAGS:
        if bag.name in existing:
            print(f"already in mosaicod, skipped: {bag.name}")
            continue
        path = OUTPUT_DIR / bag.name / f"{bag.name}.mcap"
        if not path.exists():
            path = write_bag(bag, OUTPUT_DIR)
        config = ROSInjectionConfig(
            file_path=path, sequence_name=bag.name, metadata=bag.metadata
        )
        RosbagInjector(config).run()


if __name__ == "__main__":
    main()

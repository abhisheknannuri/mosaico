"""ROS bags in a local folder, listed and named the way the SDK watchdog does."""

from datetime import datetime, timezone
from pathlib import Path

from mosaicolabs.watchdog.dispatcher import InjectorDispatcher
from mosaicolabs.watchdog.file_source import LocalFileSource
from mosaicolabs.watchdog.helpers import sequence_name_from_fileref

from mosaico_dashboard.domain.models import BagFile


def list_bag_files(folder: Path) -> list[BagFile]:
    """Supported files (.mcap, .db3, .bag) in `folder` and its subfolders, sorted by path.

    Raises ValueError if `folder` doesn't exist or isn't a folder.
    """
    source = LocalFileSource(folder, InjectorDispatcher.list_supported_ext())
    files = [
        BagFile(
            relative_path=ref.relative_path,
            path=str(source.get_local_path(ref)),
            size_bytes=ref.size,
            modified_at=datetime.fromtimestamp(ref.mtime_ns / 1e9, tz=timezone.utc),
            recording_name=sequence_name_from_fileref(ref),
        )
        for ref in source.list_files()
    ]
    return sorted(files, key=lambda f: f.relative_path)

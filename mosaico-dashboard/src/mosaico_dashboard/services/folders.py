"""The ingest folder: chosen in the UI and saved in the database, default from .env."""

from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from mosaico_dashboard.db.settings import delete_setting, get_setting, set_setting
from mosaico_dashboard.domain.models import FolderEntry, FolderListing

INGEST_DIR_KEY = "ingest_dir"
MAX_ENTRIES = 500


def get_ingest_dir(engine: Engine, default: Path | None) -> Path | None:
    """The folder saved from the UI, else `default`; `default` when the database is down."""
    try:
        with engine.connect() as connection:
            saved = get_setting(connection, INGEST_DIR_KEY)
    except SQLAlchemyError:
        return default
    return Path(saved) if saved else default


def save_ingest_dir(engine: Engine, path: str, default: Path | None) -> Path:
    """Saves the folder; choosing `default` forgets the saved one.

    Raises ValueError unless `path` is an absolute path to an existing folder.
    """
    folder = Path(path.strip()).expanduser()
    if not folder.is_absolute():
        raise ValueError("Enter an absolute path, starting with /.")
    if not folder.is_dir():
        raise ValueError(f"'{folder}' doesn't exist or isn't a folder.")
    folder = folder.resolve()
    with engine.begin() as connection:
        if default is not None and folder == default.resolve():
            delete_setting(connection, INGEST_DIR_KEY)
        else:
            set_setting(connection, INGEST_DIR_KEY, str(folder))
    return folder


def list_folder(path: str, bag_extensions: list[str]) -> FolderListing:
    """Subfolders, then files, of `path`, without hidden ones, each sorted by name."""
    folder = Path(path.strip() or "/").expanduser().resolve()
    parent = str(folder.parent) if folder.parent != folder else None
    crumbs = [
        FolderEntry(name=p.name or "/", path=str(p), is_folder=True)
        for p in [*reversed(folder.parents), folder]
    ]
    listing = FolderListing(path=str(folder), parent=parent, crumbs=crumbs, entries=[])
    try:
        children = [c for c in folder.iterdir() if not c.name.startswith(".")]
    except (FileNotFoundError, NotADirectoryError):
        return listing.model_copy(update={"error": "This folder doesn't exist."})
    except PermissionError:
        return listing.model_copy(
            update={"error": "No permission to open this folder."}
        )
    entries = [e for e in (_entry(c, bag_extensions) for c in children) if e]
    entries.sort(key=lambda e: (not e.is_folder, e.name.lower()))
    return listing.model_copy(
        update={
            "entries": entries[:MAX_ENTRIES],
            "more": max(0, len(entries) - MAX_ENTRIES),
        }
    )


def _entry(child: Path, bag_extensions: list[str]) -> FolderEntry | None:
    try:
        if child.is_dir():
            return FolderEntry(name=child.name, path=str(child), is_folder=True)
        return FolderEntry(
            name=child.name,
            path=str(child),
            is_folder=False,
            size_bytes=child.stat().st_size,
            is_bag=child.suffix.lower() in bag_extensions,
        )
    except OSError:
        return None

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from mosaico_dashboard.services.folders import (
    get_ingest_dir,
    list_folder,
    save_ingest_dir,
)

BAGS = [".mcap", ".db3", ".bag"]


def test_ingest_dir_is_the_default_until_another_is_saved(sqlite_engine, tmp_path):
    default = tmp_path / "default"
    default.mkdir()
    assert get_ingest_dir(sqlite_engine, default) == default

    save_ingest_dir(sqlite_engine, str(tmp_path), default)
    assert get_ingest_dir(sqlite_engine, default) == tmp_path

    save_ingest_dir(sqlite_engine, str(default), default)
    assert get_ingest_dir(sqlite_engine, None) is None


def test_ingest_dir_is_the_default_when_the_database_is_down():
    engine = create_engine("postgresql+psycopg://x:x@127.0.0.1:1/x")

    assert get_ingest_dir(engine, Path("/default")) == Path("/default")


@pytest.mark.parametrize(
    ("path", "message"),
    [("relative/bags", "absolute path"), ("/nope/bags", "doesn't exist")],
)
def test_save_rejects_what_is_not_a_folder(sqlite_engine, path, message):
    with pytest.raises(ValueError, match=message):
        save_ingest_dir(sqlite_engine, path, None)


def test_save_rejects_a_file(sqlite_engine, tmp_path):
    (tmp_path / "bag.mcap").write_bytes(b"x")

    with pytest.raises(ValueError, match="isn't a folder"):
        save_ingest_dir(sqlite_engine, str(tmp_path / "bag.mcap"), None)


def test_list_folder_shows_folders_then_files_without_hidden_ones(tmp_path):
    for name in ["b_run", "A_run", ".cache"]:
        (tmp_path / name).mkdir()
    (tmp_path / "drive.MCAP").write_bytes(b"xx")
    (tmp_path / "notes.txt").write_bytes(b"x")
    (tmp_path / ".hidden.mcap").write_bytes(b"x")

    listing = list_folder(str(tmp_path), BAGS)

    assert [e.name for e in listing.entries] == [
        "A_run",
        "b_run",
        "drive.MCAP",
        "notes.txt",
    ]
    assert [e.is_folder for e in listing.entries] == [True, True, False, False]
    assert [e.is_bag for e in listing.entries] == [False, False, True, False]
    assert listing.entries[2].size_bytes == 2
    assert listing.parent == str(tmp_path.parent)
    assert listing.crumbs[0].path == "/" and listing.crumbs[-1].path == str(tmp_path)


def test_list_folder_of_a_missing_folder(tmp_path):
    listing = list_folder(str(tmp_path / "nope"), BAGS)

    assert listing.entries == [] and listing.error == "This folder doesn't exist."


def test_root_has_no_parent():
    listing = list_folder("/", BAGS)

    assert listing.parent is None and [c.name for c in listing.crumbs] == ["/"]

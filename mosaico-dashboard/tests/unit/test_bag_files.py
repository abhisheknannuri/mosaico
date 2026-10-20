import pytest

from mosaico_dashboard.gateway.files import list_bag_files


@pytest.fixture
def bags(tmp_path):
    folder = tmp_path / "bags"
    (folder / "run_01").mkdir(parents=True)
    (folder / "drive.mcap").write_bytes(b"x" * 10)
    (folder / "run_01" / "lidar.db3").write_bytes(b"x" * 3)
    (folder / "run_01" / "old.bag").write_bytes(b"")
    (folder / "notes.txt").write_text("not a bag")
    (folder / "upper.MCAP").write_bytes(b"")
    return folder


def test_lists_supported_files_recursively_sorted(bags):
    files = list_bag_files(bags)

    assert [f.relative_path for f in files] == [
        "drive.mcap",
        "run_01/lidar.db3",
        "run_01/old.bag",
    ]
    assert files[0].size_bytes == 10
    assert files[0].path == str(bags / "drive.mcap")
    assert files[0].modified_at.tzinfo is not None
    assert files[0].in_mosaico is None


def test_names_follow_the_sdk_watchdog(bags):
    names = {f.relative_path: f.recording_name for f in list_bag_files(bags)}

    assert names["drive.mcap"] == "drive__mcap"
    assert names["run_01/lidar.db3"] == "run_01-lidar__db3"


def test_missing_folder(tmp_path):
    with pytest.raises(ValueError):
        list_bag_files(tmp_path / "nope")

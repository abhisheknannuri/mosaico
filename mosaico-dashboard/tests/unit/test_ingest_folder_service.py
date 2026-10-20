from mosaico_dashboard.gateway.fake import (
    FakeGateway,
    sample_recordings,
    sample_streams,
)
from mosaico_dashboard.services.ingestion import find_bag_file, get_ingest_folder


def gateway_with_recording(name: str) -> FakeGateway:
    recording = sample_recordings(sample_streams())[0].model_copy(update={"name": name})
    return FakeGateway(recordings=[recording])


def test_folder_not_configured():
    folder = get_ingest_folder(FakeGateway(), None)

    assert (folder.status, folder.path, folder.files) == ("not_configured", None, [])


def test_folder_missing(tmp_path):
    folder = get_ingest_folder(FakeGateway(), tmp_path / "nope")

    assert folder.status == "missing"


def test_files_already_in_mosaico_are_marked(tmp_path):
    (tmp_path / "a.mcap").write_bytes(b"")
    (tmp_path / "b.mcap").write_bytes(b"")

    folder = get_ingest_folder(gateway_with_recording("a__mcap"), tmp_path)

    assert folder.status == "ok"
    assert {f.relative_path: f.in_mosaico for f in folder.files} == {
        "a.mcap": True,
        "b.mcap": False,
    }


def test_unknown_when_mosaicod_is_down(tmp_path):
    (tmp_path / "a.mcap").write_bytes(b"")

    folder = get_ingest_folder(FakeGateway(available=False), tmp_path)

    assert folder.status == "ok"
    assert folder.files[0].in_mosaico is None


def test_only_listed_files_can_be_selected(tmp_path):
    (tmp_path / "a.mcap").write_bytes(b"")
    folder = get_ingest_folder(FakeGateway(), tmp_path)

    assert find_bag_file(folder, "a.mcap") is not None
    assert find_bag_file(folder, "../etc/passwd") is None
    assert find_bag_file(folder, None) is None

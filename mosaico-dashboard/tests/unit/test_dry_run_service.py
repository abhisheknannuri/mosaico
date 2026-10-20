from datetime import datetime, timezone

import pytest

from mosaico_dashboard.domain.models import BagFile
from mosaico_dashboard.gateway.fake import FakeGateway
from mosaico_dashboard.services.ingestion import dry_run_ingestion, metadata_from_rows

FILE = BagFile(
    relative_path="run_01/drive.mcap",
    path="/bags/run_01/drive.mcap",
    size_bytes=10,
    modified_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    recording_name="run_01-drive__mcap",
)


def test_metadata_rows_skip_empty_keys_and_strip():
    rows = metadata_from_rows([" project ", "", "robot"], [" wh ", "x", "carter"])

    assert rows == {"project": "wh", "robot": "carter"}


def test_metadata_duplicate_key():
    with pytest.raises(ValueError, match="'robot' is used twice"):
        metadata_from_rows(["robot", "robot"], ["a", "b"])


def test_dry_run_builds_the_request():
    result = dry_run_ingestion(
        FakeGateway(), FILE, " my_run ", ["project"], ["warehouse"]
    )

    assert result.request is not None
    assert result.request.file_path == "/bags/run_01/drive.mcap"
    assert result.request.sequence_name == "my_run"
    assert result.request.metadata == {"project": "warehouse"}
    assert result.verdict == "warn"


def test_invalid_name_is_reported_without_a_dry_run():
    result = dry_run_ingestion(FakeGateway(), FILE, "my run", [], [])

    assert result.request is None
    assert result.error is not None and "space" in result.error


def test_duplicate_metadata_is_reported():
    result = dry_run_ingestion(FakeGateway(), FILE, "ok", ["a", "a"], ["1", "2"])

    assert result.error == "The metadata key 'a' is used twice."


def test_sdk_errors_are_reported():
    class Unreadable(FakeGateway):
        def dry_run(self, request):
            raise RuntimeError("Unable to initialize ROSLoader")

    result = dry_run_ingestion(Unreadable(), FILE, "ok", [], [])

    assert result.verdict == "blocked"
    assert result.error == "Unable to initialize ROSLoader"

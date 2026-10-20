import pytest

from mosaico_dashboard.domain.format import format_number
from mosaico_dashboard.domain.models import (
    DryRun,
    DryRunTopic,
    IngestRequest,
    recording_name_problem,
)

REQUEST = IngestRequest(file_path="/bags/a.mcap", sequence_name="a")
OK = DryRunTopic(name="/imu", accepted=True, adapter="IMUAdapter", msg_count=10)
SKIPPED = DryRunTopic(name="/custom", accepted=False, reason="Unresolved adapter")


@pytest.mark.parametrize(
    "name", ["run_01-drive__mcap", "warehouse-run-02", "A1", "with(parens)"]
)
def test_valid_recording_names(name):
    assert recording_name_problem(name) is None


@pytest.mark.parametrize(
    "name, shown",
    [
        ("my run", "space"),
        ("run.01", "."),
        ("a/b", "/"),
        ("a:b", ":"),
        ("prix£", "£"),
        ("caffè", "è"),
        ("tab\there", "\t"),
    ],
)
def test_names_mosaicod_refuses(name, shown):
    problem = recording_name_problem(name)

    assert problem is not None and shown in problem


def test_empty_name():
    assert recording_name_problem("") == "Enter a recording name."


def test_verdicts():
    assert DryRun(request=REQUEST, topics=[OK]).verdict == "ok"
    assert DryRun(request=REQUEST, topics=[OK, SKIPPED]).verdict == "warn"
    assert DryRun(request=REQUEST, topics=[SKIPPED]).verdict == "blocked"
    assert DryRun(request=REQUEST, error="unreadable").verdict == "blocked"


def test_message_count_only_counts_accepted_topics():
    assert DryRun(request=REQUEST, topics=[OK, SKIPPED]).message_count == 10


def test_format_number():
    assert format_number(12000) == "12,000"
    assert format_number(None) == "—"

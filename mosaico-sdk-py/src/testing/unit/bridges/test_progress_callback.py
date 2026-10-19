from pathlib import Path

import pytest

from mosaicolabs.bridges import ui as ui_module
from mosaicolabs.bridges.mcap.injector import MCAPInjectionConfig
from mosaicolabs.bridges.mcap.sequence_extractor import MCAPExtractorConfig
from mosaicolabs.bridges.ros.injector import ROSInjectionConfig
from mosaicolabs.bridges.ros.sequence_extractor import ROSExtractorConfig
from mosaicolabs.bridges.topic_status import TopicStatus
from mosaicolabs.bridges.ui import ProgressManager, ProgressSnapshot


class _FakeLoader:
    """Two accepted topics (/imu: 3 messages, /gps: 2), one rejected."""

    topics = ["/imu", "/gps"]
    resolved_topics = ["/imu", "/gps", "/custom"]
    rejected_topics = [("/custom", TopicStatus.UNRESOLVED_ADAPTER)]

    def msg_count(self, topic=None):
        return {"/imu": 3, "/gps": 2}[topic]


@pytest.fixture
def snapshots() -> list[ProgressSnapshot]:
    return []


def _manager(snapshots, interval_s: float, monkeypatch) -> ProgressManager:
    monkeypatch.setattr(ui_module, "PROGRESS_CALLBACK_INTERVAL_S", interval_s)
    manager = ProgressManager(_FakeLoader(), snapshots.append)
    manager.setup()
    return manager


def test_setup_reports_totals_and_rejected_topics(snapshots, monkeypatch):
    _manager(snapshots, 0.0, monkeypatch)

    first = snapshots[0]
    assert (first.done, first.total, first.finished) == (0, 5, False)
    topics = {t.name: t for t in first.topics}
    assert (topics["/imu"].done, topics["/imu"].total) == (0, 3)
    assert topics["/custom"].total is None
    assert topics["/custom"].status == "Unresolved adapter"


def test_progress_counts_written_and_skipped_messages(snapshots, monkeypatch):
    manager = _manager(snapshots, 0.0, monkeypatch)

    manager.advance_all("/imu")
    manager.advance_all("/imu")
    manager.update_status("/gps", "Write Error", "red")
    manager.advance_global()
    manager.finish()

    last = snapshots[-1]
    topics = {t.name: t for t in last.topics}
    assert (last.done, last.total, last.finished) == (3, 5, True)
    assert topics["/imu"].done == 2
    assert topics["/gps"].status == "Write Error"


def test_callbacks_are_throttled_but_setup_and_finish_always_report(
    snapshots, monkeypatch
):
    manager = _manager(snapshots, 3600.0, monkeypatch)

    for _ in range(5):
        manager.advance_all("/imu")
    manager.finish()

    assert [s.finished for s in snapshots] == [False, True]
    assert snapshots[-1].done == 5


def test_a_failing_callback_does_not_stop_the_run(monkeypatch):
    def broken(snapshot):
        raise ValueError("display is gone")

    manager = ProgressManager(_FakeLoader(), broken)
    manager.setup()
    manager.advance_all("/imu")
    manager.finish()

    assert manager.snapshot().done == 1


def test_without_a_callback_nothing_is_reported():
    manager = ProgressManager(_FakeLoader())
    manager.setup()
    manager.advance_all("/imu")
    manager.finish()

    assert manager.snapshot().done == 1


@pytest.mark.parametrize(
    "config",
    [
        ROSInjectionConfig(file_path=Path("a.mcap"), sequence_name="a"),
        MCAPInjectionConfig(file_path=Path("a.mcap"), sequence_name="a"),
        ROSExtractorConfig(saving_path=Path("out"), sequence_name="a"),
        MCAPExtractorConfig(saving_path=Path("out"), sequence_name="a"),
    ],
)
def test_configs_accept_a_progress_callback(config):
    assert config.progress_callback is None

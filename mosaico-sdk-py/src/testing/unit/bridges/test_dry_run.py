from pathlib import Path

import pytest

from mosaicolabs.bridges.base_injector import DryRunReport, InjectionStatus
from mosaicolabs.bridges.mcap.injector import MCAPInjectionConfig, MCAPInjector
from mosaicolabs.bridges.ros.injector import RosbagInjector, ROSInjectionConfig
from mosaicolabs.bridges.topic_status import TopicStatus


class _ImuAdapter:
    pass


class _OverrideAdapter:
    pass


class _FakeLoader:
    """Stands in for ROSLoader / MCAPLoader: two accepted topics, two rejected."""

    topics = ["/imu", "/gps"]
    rejected_topics = [
        ("/custom", TopicStatus.UNRESOLVED_ADAPTER),
        ("/debug", TopicStatus.FILTERED),
    ]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def msg_count(self, topic=None):
        return {"/imu": 200, "/gps": 10}[topic]

    def resolve_adapter(self, topic):
        return _ImuAdapter if topic == "/imu" else None


def _ros_injector(**overrides) -> RosbagInjector:
    config = ROSInjectionConfig(
        file_path=Path("run.mcap"), sequence_name="run", **overrides
    )
    injector = RosbagInjector(config)
    injector._loader = _FakeLoader()
    return injector


def _mcap_injector(**overrides) -> MCAPInjector:
    config = MCAPInjectionConfig(
        file_path=Path("run.mcap"), sequence_name="run", **overrides
    )
    injector = MCAPInjector(config)
    injector._loader = _FakeLoader()
    return injector


@pytest.mark.parametrize("make_injector", [_ros_injector, _mcap_injector])
def test_dry_run_returns_accepted_and_rejected_topics(make_injector):
    report = make_injector().dry_run()

    assert isinstance(report, DryRunReport)
    assert report.file_path == Path("run.mcap")
    assert report.sequence_name == "run"
    assert [(t.name, t.adapter, t.msg_count) for t in report.accepted_topics] == [
        ("/imu", "_ImuAdapter", 200),
        ("/gps", None, 10),
    ]
    assert [(t.name, t.status) for t in report.rejected_topics] == [
        ("/custom", TopicStatus.UNRESOLVED_ADAPTER),
        ("/debug", TopicStatus.FILTERED),
    ]
    assert all(t.msg_count is None for t in report.rejected_topics)


@pytest.mark.parametrize("make_injector", [_ros_injector, _mcap_injector])
def test_dry_run_lists_unused_topic_metadata(make_injector):
    injector = make_injector(topic_metadata={"/imu": {"a": 1}, "/debug": {"b": 2}})

    assert injector.dry_run().unused_topic_metadata == ["/debug"]


def test_ros_dry_run_reports_adapter_overrides():
    injector = _ros_injector(adapter_overrides={"/gps": _OverrideAdapter})

    adapters = {t.name: t.adapter for t in injector.dry_run().accepted_topics}

    assert adapters == {"/imu": "_ImuAdapter", "/gps": "_OverrideAdapter"}


@pytest.mark.parametrize("make_injector", [_ros_injector, _mcap_injector])
def test_run_in_dry_run_mode_prints_the_report(make_injector, capsys):
    status = make_injector(dry_run=True).run()

    printed = capsys.readouterr().err
    assert status == InjectionStatus.DRY_RUN
    assert "/imu" in printed and "/custom" in printed
    assert "2 topic(s) would be ingested" in printed

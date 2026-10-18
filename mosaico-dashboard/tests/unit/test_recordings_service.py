from mosaico_dashboard.gateway.fake import (
    RECORDED_AT,
    FakeGateway,
    sample_recordings,
    sample_streams,
)
from mosaico_dashboard.services.recordings import list_recording_summaries


def test_summaries_have_sensor_categories():
    summaries = {s.recording.name: s for s in list_recording_summaries(FakeGateway())}

    assert summaries["r2b_galileo2_0"].sensor_categories == [
        "Camera",
        "Motion",
        "Other",
        "Robot state",
        "Transform",
    ]
    assert summaries["r2b_robotarm_0"].sensor_categories == ["Camera", "Robot state"]


def test_newest_recorded_first_and_undated_last():
    streams = sample_streams()
    galileo, robotarm = sample_recordings(streams)
    later = robotarm.model_copy(update={"data_start": RECORDED_AT.replace(year=2025)})
    undated = galileo.model_copy(update={"name": "undated", "data_start": None})
    gateway = FakeGateway(recordings=[undated, galileo, later], streams=streams)

    names = [s.recording.name for s in list_recording_summaries(gateway)]

    assert names == ["r2b_robotarm_0", "r2b_galileo2_0", "undated"]


def test_empty_catalog():
    assert list_recording_summaries(FakeGateway(recordings=[], streams=[])) == []

"""Gateway backed by the Mosaico SDK (one shared client, fresh data on every call)."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.flight as flight
from mosaicolabs import MosaicoClient, SequenceHandler, TopicHandler

from mosaico_dashboard.domain.models import Recording, SensorStream, Upload
from mosaico_dashboard.gateway.base import (
    GatewayError,
    GatewayUnavailable,
    MosaicoGateway,
    RecordingNotFound,
)


class SdkGateway(MosaicoGateway):
    def __init__(
        self,
        host: str,
        port: int,
        api_key: str | None = None,
        tls: bool = False,
        tls_cert_path: Path | None = None,
        connect_timeout: int = 2,
    ):
        self._host = host
        self._port = port
        self._api_key = api_key
        self._tls = tls
        self._tls_cert_path = tls_cert_path
        self._connect_timeout = connect_timeout
        self._client: MosaicoClient | None = None
        self._lock = threading.Lock()

    def check_connection(self) -> str:
        with _translate_errors():
            client = self._fresh_client()
            client.list_sequences()
            return client.info().version

    def list_recordings(self) -> list[Recording]:
        with _translate_errors():
            client = self._fresh_client()
            recordings = []
            for name in client.list_sequences():
                handler = client.sequence_handler(name)
                if handler is not None:
                    recordings.append(_to_recording(handler))
            return recordings

    def get_recording(self, name: str) -> Recording:
        with _translate_errors():
            client = self._fresh_client()
            return _to_recording(_sequence_handler(client, name))

    def list_streams(self, recording: str) -> list[SensorStream]:
        with _translate_errors():
            client = self._fresh_client()
            handler = _sequence_handler(client, recording)
            streams = []
            for topic in handler.topics:
                topic_handler = client.topic_handler(recording, topic)
                if topic_handler is not None:
                    streams.append(_to_sensor_stream(recording, topic, topic_handler))
            return streams

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def _fresh_client(self) -> MosaicoClient:
        """The shared client, connected on first use, with its handler caches cleared."""
        with self._lock:
            if self._client is None:
                self._client = self._connect()
            client = self._client
        client.clear_sequence_handlers_cache()
        client.clear_topic_handlers_cache()
        return client

    def _connect(self) -> MosaicoClient:
        try:
            return MosaicoClient.connect(
                self._host,
                self._port,
                timeout=self._connect_timeout,
                enable_tls=self._tls,
                tls_cert_path=str(self._tls_cert_path) if self._tls_cert_path else None,
                api_key=self._api_key,
            )
        except ConnectionError as error:
            raise GatewayUnavailable(
                f"mosaicod at {self._host}:{self._port} is not reachable"
            ) from error


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except (flight.FlightUnavailableError, flight.FlightTimedOutError) as error:
        raise GatewayUnavailable(str(error)) from error
    except flight.FlightError as error:
        raise GatewayError(str(error)) from error


def _sequence_handler(client: MosaicoClient, name: str) -> SequenceHandler:
    """Raises RecordingNotFound."""
    if name not in client.list_sequences():
        raise RecordingNotFound(name)
    handler = client.sequence_handler(name)
    if handler is None:
        raise RecordingNotFound(name)
    return handler


def _to_datetime(timestamp_ns: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc)


def _to_optional_datetime(timestamp_ns: int | None) -> datetime | None:
    return None if timestamp_ns is None else _to_datetime(timestamp_ns)


def _to_recording(handler: SequenceHandler) -> Recording:
    return Recording(
        name=handler.name,
        uploaded_at=_to_datetime(handler.created_timestamp),
        data_start=_to_optional_datetime(handler.timestamp_ns_min),
        data_end=_to_optional_datetime(handler.timestamp_ns_max),
        size_bytes=handler.total_size_bytes,
        metadata=handler.user_metadata,
        uploads=[
            Upload(
                id=session.locator,
                started_at=_to_datetime(session.created_timestamp),
                completed_at=_to_optional_datetime(session.completed_timestamp),
                topics=session.topics,
            )
            for session in handler.sessions
        ],
    )


def _to_sensor_stream(
    recording: str, topic: str, handler: TopicHandler
) -> SensorStream:
    ros = handler.user_metadata.get("_ros_", {})
    return SensorStream(
        recording=recording,
        topic=topic,
        ontology_tag=handler.ontology_tag,
        ros_type=ros.get("msgtype") if isinstance(ros, dict) else None,
        size_bytes=handler.total_size_bytes,
        data_start=_to_optional_datetime(handler.timestamp_ns_min),
        data_end=_to_optional_datetime(handler.timestamp_ns_max),
    )

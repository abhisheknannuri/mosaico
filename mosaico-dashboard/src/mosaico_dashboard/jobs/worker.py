"""Worker loop: claim the oldest queued job and run it in a child process."""

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from mosaico_dashboard.db.jobs import claim_next, fail_interrupted, finish, get_job
from mosaico_dashboard.db.workers import heartbeat, register_worker, unregister_worker
from mosaico_dashboard.domain.models import Job
from mosaico_dashboard.logging_config import get_logger

logger = get_logger(__name__)

CHECK_SECONDS = 0.5
HEARTBEAT_SECONDS = 2.0
KILL_AFTER_SECONDS = 60.0


def child_command(job_id: str) -> list[str]:
    return [sys.executable, "-m", "mosaico_dashboard.jobs.run_job", job_id]


class Worker:
    def __init__(
        self,
        engine: Engine,
        poll_seconds: float = 1.0,
        command: Callable[[str], list[str]] = child_command,
    ):
        self._engine = engine
        self._poll_seconds = poll_seconds
        self._command = command
        self._stop = threading.Event()
        self._database_ok = True
        self._last_heartbeat = 0.0

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            with self._engine.begin() as connection:
                interrupted = fail_interrupted(connection)
                register_worker(connection, os.getpid())
            if interrupted:
                logger.warning("Marked %d interrupted job(s) as failed", interrupted)
        except SQLAlchemyError as error:
            logger.warning("Database unavailable at start: %s", error)
        try:
            self._loop()
        finally:
            try:
                with self._engine.begin() as connection:
                    unregister_worker(connection)
            except SQLAlchemyError:
                pass

    def _heartbeat(self, force: bool = False) -> None:
        """Tells the dashboard the worker is alive; stops when a stop was requested."""
        if not force and time.monotonic() - self._last_heartbeat < HEARTBEAT_SECONDS:
            return
        self._last_heartbeat = time.monotonic()
        try:
            with self._engine.begin() as connection:
                stop_requested = heartbeat(connection)
        except SQLAlchemyError:
            return
        if stop_requested and not self._stop.is_set():
            logger.info("Stop requested from the dashboard")
            self.stop()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._heartbeat(force=True)
            if self._stop.is_set():
                break
            try:
                worked = self.run_once()
                if not self._database_ok:
                    logger.info("Database available again")
                    self._database_ok = True
            except SQLAlchemyError as error:
                if self._database_ok:
                    logger.warning("Database unavailable, retrying: %s", error)
                    self._database_ok = False
                worked = False
            if not worked:
                self._stop.wait(self._poll_seconds)

    def run_once(self) -> bool:
        """Runs one job to its end. False when the queue is empty."""
        with self._engine.begin() as connection:
            job = claim_next(connection)
        if job is None:
            return False
        logger.info("Job %s started: %s %s", job.id, job.kind, job.params)
        exit_code, interrupted = self._run_child(job)
        with self._engine.begin() as connection:
            current = get_job(connection, job.id)
            if current is not None and current.status == "running":
                if interrupted:
                    finish(connection, job.id, "cancelled")
                else:
                    finish(
                        connection,
                        job.id,
                        "failed",
                        f"The job process stopped unexpectedly (exit code {exit_code}).",
                    )
            current = get_job(connection, job.id)
        logger.info("Job %s %s", job.id, current.status if current else "gone")
        return True

    def _run_child(self, job: Job) -> tuple[int, bool]:
        """Waits for the child; sends it Ctrl-C (SIGINT) on cancel or worker stop."""
        process = subprocess.Popen(self._command(job.id), start_new_session=True)
        interrupted_at: float | None = None
        while process.poll() is None:
            self._heartbeat()
            if interrupted_at is None and (
                self._stop.is_set() or self._cancel_requested(job.id)
            ):
                process.send_signal(signal.SIGINT)
                interrupted_at = time.monotonic()
            elif (
                interrupted_at is not None
                and time.monotonic() - interrupted_at > KILL_AFTER_SECONDS
            ):
                process.kill()
            time.sleep(CHECK_SECONDS)
        return process.returncode, interrupted_at is not None

    def _cancel_requested(self, job_id: str) -> bool:
        try:
            with self._engine.connect() as connection:
                job = get_job(connection, job_id)
        except SQLAlchemyError:
            return False
        return job is not None and job.cancel_requested

"""Background processes the web app starts on demand and stops on shutdown, by name."""

import signal
import subprocess
import sys
from collections.abc import Mapping, Sequence

from mosaico_dashboard.logging_config import get_logger

logger = get_logger(__name__)

COMMANDS = {
    "worker": (sys.executable, "-m", "mosaico_dashboard.run_worker"),
}
STOP_TIMEOUT_SECONDS = 70


class ProcessManager:
    def __init__(self, commands: Mapping[str, Sequence[str]] = COMMANDS):
        self._commands = {name: list(command) for name, command in commands.items()}
        self._processes: dict[str, subprocess.Popen] = {}

    def is_alive(self, name: str) -> bool:
        """True while a process this manager started under `name` has not exited."""
        process = self._processes.get(name)
        return process is not None and process.poll() is None

    def start(self, name: str) -> None:
        """Starts the process unless the one started earlier is still alive."""
        if self.is_alive(name):
            return
        process = subprocess.Popen(self._commands[name], start_new_session=True)
        self._processes[name] = process
        logger.info("Started %s (pid %d)", name, process.pid)

    def stop(self, name: str) -> None:
        """SIGTERM, then kill after STOP_TIMEOUT_SECONDS."""
        process = self._processes.pop(name, None)
        if process is None or process.poll() is not None:
            return
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
        logger.info("Stopped %s", name)

    def stop_all(self) -> None:
        for name in list(self._processes):
            self.stop(name)

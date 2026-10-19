import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, Tuple

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from mosaicolabs.logging_config import get_logger

from .topic_status import TopicStatus, to_color

# Set the hierarchical logger
logger = get_logger(__name__)

PROGRESS_CALLBACK_INTERVAL_S = 0.5
"""Minimum time between two progress callbacks while messages are processed."""


@dataclass(frozen=True)
class TopicProgress:
    """
    Progress of one topic.

    Attributes:
        name (str): The topic (or MCAP channel) name.
        done (int): Messages of this topic processed so far.
        total (Optional[int]): Messages of this topic in the source; `None` for rejected
            topics, which are not processed.
        status (Optional[str]): Last status set for the topic (the rejection reason, or e.g.
            "Write Error"); `None` while nothing was reported.
    """

    name: str
    done: int
    total: Optional[int]
    status: Optional[str]


@dataclass(frozen=True)
class ProgressSnapshot:
    """
    Progress of a whole run, passed to a `ProgressCallback`.

    Attributes:
        topics (List[TopicProgress]): Every topic of the source, accepted and rejected.
        done (int): Messages processed so far (written, skipped or failed).
        total (int): Messages of the accepted topics.
        finished (bool): `True` once every message has been processed; the run then
            finalizes the sequence (or the output file), and its result is the outcome of
            `run()`.
    """

    topics: List[TopicProgress]
    done: int
    total: int
    finished: bool


ProgressCallback = Callable[[ProgressSnapshot], None]
"""Receives the progress of a run: after setup, at most every
`PROGRESS_CALLBACK_INTERVAL_S` while messages are processed, and once when finished."""


# --- Generic Protocol for ProgressManager LoaderUIAPI ---
class LoaderUIAPI(Protocol):
    """
    Structural protocol for data loaders consumed by :class:`ProgressManager`.

    :class:`ROSLoader`, :class:`MosaicoLoader`, and :class:`MCAPLoader` all satisfy
    this protocol, allowing :class:`ProgressManager` to set up progress bars without
    depending on a concrete loader class.
    """

    @property
    def topics(self) -> List[str]:
        """This should return the Mosaico compatible topics of the loaded data as strings"""
        ...

    @property
    def resolved_topics(self) -> List[str]:
        """This should return **all** the topics of the loaded data as strings"""
        ...

    @property
    def rejected_topics(self) -> List[Tuple[str, TopicStatus]]:
        """This should return a list of tuples containing all the rejected topic names, and the rejection reason (topic_name, topic_status)"""
        ...

    def msg_count(self, topic: Optional[str] = None) -> int:
        """This should return the total number of messages in the passed
        topic if not None. Otherwise returns all messages in all topics"""
        ...


# --- UI / Progress Helper ---


class ProgressManager:
    """
    Visual management system for loader tracking.

    This class decouples the UI presentation logic from the data processing pipeline.
    It utilizes the `rich` library to provide real-time feedback through progress bars,
    tracking individual topic throughput and aggregate global progress.


    Methods:
        setup(): Initializes the progress tracking tasks by querying message counts from the loader.
        update_status(topic, status, style): Modifies the label of a specific topic bar.
        advance_global(): Increments the master progress bar without affecting individual topic bars.
        advance_all(topic): Increments both the specific topic task and the global master task.
    """

    def __init__(
        self, loader: LoaderUIAPI, callback: Optional[ProgressCallback] = None
    ):
        """
        Initialize the progress manager.

        Args:
            loader (LoaderUIAPI): The initialized data loader. Used to query total
                                message counts for setting up progress bars.
            callback (Optional[ProgressCallback]): Also receives the progress as data, e.g. to
                show it outside the terminal. An exception raised by it is logged and does
                not stop the run.
        """
        self.loader = loader
        self.callback = callback
        self.statuses: Dict[str, str] = {}
        self._last_callback = 0.0
        self.progress = Progress(
            TextColumn("[bold cyan]{task.fields[name]}"),
            BarColumn(),
            MofNCompleteColumn(),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TimeRemainingColumn(),
            "•",
            TimeElapsedColumn(),
            expand=True,
        )
        self.tasks: Dict[str, TaskID] = {}
        self.global_task: Optional[TaskID] = None

    def setup(self):
        """
        Calculates totals and creates the visual progress tasks.
        Must be called before the main processing loop starts.
        """
        # Create individual progress bars for each topic but count only the accepted ones
        for topic_name in self.loader.resolved_topics:
            if topic_name in self.loader.topics:
                count = self.loader.msg_count(topic_name)
            else:
                count = None

            self.tasks[topic_name] = self.progress.add_task(
                "", total=count, name=topic_name
            )

        # Rejected topics (with rejected reason) are highlighted
        for topic_name, topic_status in self.loader.rejected_topics:
            self.update_status(topic_name, topic_status.value, to_color(topic_status))

        # Create a master progress bar for the aggregate total of the accepted topics
        total_msgs = sum(self.loader.msg_count(t) for t in self.loader.topics)
        self.global_task = self.progress.add_task(
            "Total", total=total_msgs, name="Total Upload"
        )
        self._notify(force=True)

    def update_status(self, topic: str, status: str, style: str = "white"):
        """
        Updates the text description of a specific topic's progress bar.
        Useful for indicating errors or skipped topics (e.g. "[red]Unresolved Adapter").

        Args:
            topic (str): The topic name.
            status (str): The status message to display.
            style (str): The rich style string (e.g., 'red', 'bold yellow').
        """
        if topic in self.tasks:
            self.progress.update(
                self.tasks[topic],
                name=f"[{style}]{topic}: {status}",
            )
            self.statuses[topic] = status
            self._notify()

    def advance_global(self):
        """Advances only the global progress bar (used when skipping messages)."""
        if self.global_task is not None:
            self.progress.advance(self.global_task)
        self._notify()

    def advance_all(self, topic: str):
        """Advances both the specific topic's bar and the global bar."""
        if topic in self.tasks:
            self.progress.advance(self.tasks[topic])
        if self.global_task is not None:
            self.progress.advance(self.global_task)
        self._notify()

    def finish(self):
        """Reports that every message has been processed (to the callback, if any)."""
        self._notify(force=True, finished=True)

    def snapshot(self, finished: bool = False) -> ProgressSnapshot:
        """The current progress as data."""
        tasks = {task.id: task for task in self.progress.tasks}
        topics = [
            TopicProgress(
                name=name,
                done=int(tasks[task_id].completed),
                total=None
                if tasks[task_id].total is None
                else int(tasks[task_id].total),
                status=self.statuses.get(name),
            )
            for name, task_id in self.tasks.items()
        ]
        overall = tasks.get(self.global_task) if self.global_task is not None else None
        return ProgressSnapshot(
            topics=topics,
            done=int(overall.completed) if overall else 0,
            total=int(overall.total or 0) if overall else 0,
            finished=finished,
        )

    def _notify(self, force: bool = False, finished: bool = False):
        if self.callback is None or self.global_task is None:
            return
        now = time.monotonic()
        if not force and now - self._last_callback < PROGRESS_CALLBACK_INTERVAL_S:
            return
        self._last_callback = now
        try:
            self.callback(self.snapshot(finished))
        except Exception as e:
            logger.warning(f"Progress callback failed: '{e}'")

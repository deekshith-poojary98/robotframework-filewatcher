from collections import deque
from pathlib import Path
import threading
import time
from typing import Iterator

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from FileWatcher.exceptions import (
    DirectoryAlreadyWatchedError,
    DirectoryNotWatchedError,
    FileWatcherError,
    FileWatcherTimeoutError,
)
from FileWatcher.models import EventIdGenerator, EventType, FileEvent


class EventStore:
    """A thread-safe, non-consuming, in-memory store for file events.

    Retains history using a double-ended queue (deque) with a configurable maximum size.
    Waiters can block efficiently using a condition variable without busy waiting.
    """

    def __init__(self, max_events: int = 10000) -> None:
        """Initializes the EventStore.

        Args:
            max_events (int): The maximum number of events to retain in memory.
        """
        self._max_events = max_events
        self._condition = threading.Condition()
        self._events: deque[FileEvent] = deque(maxlen=max_events)

    def push(self, event: FileEvent) -> None:
        """Appends a new event to the store and notifies all waiting threads.

        Args:
            event (FileEvent): The file event to add.
        """
        with self._condition:
            self._events.append(event)
            self._condition.notify_all()

    def get_all(self) -> list[FileEvent]:
        """Returns a snapshot list of all retained events.

        Returns:
            list[FileEvent]: A copy of the currently retained events.
        """
        with self._condition:
            return list(self._events)

    def get_since(self, event_id: int) -> list[FileEvent]:
        """Returns a snapshot list of events with an ID greater than event_id.

        Args:
            event_id (int): The starting threshold ID.

        Returns:
            list[FileEvent]: A list of events occurring after event_id.
        """
        with self._condition:
            return [event for event in self._events if event.id > event_id]

    def get_current_event_id(self) -> int:
        """Returns the ID of the most recent event.

        Returns:
            int: The maximum event ID currently stored, or 0 if empty.
        """
        with self._condition:
            if not self._events:
                return 0
            return self._events[-1].id

    def clear(self) -> None:
        """Removes all stored events. Thread-safe."""
        with self._condition:
            self._events.clear()

    def wait_for_event(
        self,
        event_type: EventType | None = None,
        pattern: str | None = None,
        since_id: int = 0,
        timeout: float = 30.0,
    ) -> FileEvent:
        """Blocks until a matching event is recorded or the timeout is exceeded.

        First scans the existing history for a match. If not found, blocks
        using a condition variable.

        Args:
            event_type (EventType | None): Optional type of event to match.
            pattern (str | None): Optional glob pattern to match.
            since_id (int): Match only events with ID greater than this value.
            timeout (float): Maximum time to wait in seconds.

        Returns:
            FileEvent: The first matching file event.

        Raises:
            FileWatcherTimeoutError: If no matching event is found within the timeout.
        """
        deadline = time.time() + timeout
        with self._condition:
            while True:
                # 1. Scan current list
                for event in self._events:
                    if event.id > since_id:
                        if event_type is not None and event.event_type != event_type:
                            continue
                        if pattern is not None and not event.matches_glob(pattern):
                            continue
                        return event

                # 2. Check timeout
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise FileWatcherTimeoutError(
                        f"Timed out waiting for file event (pattern={pattern}, "
                        f"event_type={event_type}, since_id={since_id}) after {timeout} seconds."
                    )

                # 3. Wait for notification
                self._condition.wait(timeout=remaining)

    def __len__(self) -> int:
        """Returns the number of currently stored events.

        Returns:
            int: The size of the store.
        """
        with self._condition:
            return len(self._events)

    def __repr__(self) -> str:
        """Returns string representation of the EventStore.

        Returns:
            str: Representative string.
        """
        with self._condition:
            return f"EventStore(events={len(self._events)}, max_events={self._max_events})"


class DirectoryEventHandler(FileSystemEventHandler):
    """Bridges watchdog raw OS events to our EventStore using FileEvent models."""

    def __init__(
        self,
        watched_directory: Path,
        event_store: EventStore,
        id_generator: EventIdGenerator,
    ) -> None:
        """Initializes the DirectoryEventHandler.

        Args:
            watched_directory (Path): Root directory path monitored by this handler.
            event_store (EventStore): Targets incoming events to this store.
            id_generator (EventIdGenerator): Generator for unique event IDs.
        """
        super().__init__()
        self.watched_directory = watched_directory
        self.event_store = event_store
        self.id_generator = id_generator

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handles any filesystem event, normalization, and pushing to EventStore."""
        try:
            event_type = EventType(event.event_type)
        except ValueError:
            # Ignore event types we don't track
            return

        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path) if getattr(event, "dest_path", None) is not None else None

        file_event = FileEvent(
            id=self.id_generator.next_id(),
            event_type=event_type,
            src_path=src_path,
            dest_path=dest_path,
            watched_directory=self.watched_directory,
            timestamp=time.time(),
        )
        self.event_store.push(file_event)


class WatchManager:
    """Orchestrates file system observers and directory watches using watchdog."""

    def __init__(self, max_events: int = 10000) -> None:
        """Initializes the WatchManager.

        Args:
            max_events (int): Event retention size.
        """
        self._event_store = EventStore(max_events)
        self._event_id_generator = EventIdGenerator()
        self._watches: dict[Path, ObservedWatch] = {}
        self._handlers: dict[Path, DirectoryEventHandler] = {}
        self._lock = threading.RLock()
        self._observer: Observer | None = None

    def _get_observer(self) -> Observer:
        """Returns the watchdog Observer instance, creating it if not exist."""
        # Must be called under lock
        if self._observer is None:
            self._observer = Observer()
        return self._observer

    def _ensure_observer_running(self) -> None:
        """Starts the observer background thread if it is not already running."""
        # Must be called under lock
        observer = self._get_observer()
        if not observer.is_alive():
            try:
                observer.start()
            except RuntimeError:
                # The thread has already been stopped once; recreate it
                self._observer = Observer()
                self._observer.start()

    def start_watch(self, path: Path | str, recursive: bool = True) -> None:
        """Starts monitoring a directory path for events.

        Args:
            path (Path | str): The directory path to monitor.
            recursive (bool): Whether to watch subdirectories.

        Raises:
            FileWatcherError: If path is invalid or does not exist.
            DirectoryAlreadyWatchedError: If path is already monitored.
        """
        with self._lock:
            try:
                resolved_path = Path(path).resolve(strict=True)
            except (OSError, FileNotFoundError) as err:
                raise FileWatcherError(f"Path does not exist: {path}") from err

            if not resolved_path.is_dir():
                raise FileWatcherError(f"Path is not a directory: {path}")

            if resolved_path in self._watches:
                raise DirectoryAlreadyWatchedError(f"Directory is already watched: {path}")

            handler = DirectoryEventHandler(
                watched_directory=resolved_path,
                event_store=self._event_store,
                id_generator=self._event_id_generator,
            )

            observer = self._get_observer()
            self._ensure_observer_running()

            watch = observer.schedule(handler, str(resolved_path), recursive=recursive)
            self._watches[resolved_path] = watch
            self._handlers[resolved_path] = handler

    def stop_watch(self, path: Path | str) -> None:
        """Stops monitoring a directory path.

        Args:
            path (Path | str): The directory path to stop monitoring.

        Raises:
            DirectoryNotWatchedError: If path was not registered.
        """
        with self._lock:
            resolved_path = Path(path).resolve()
            if resolved_path not in self._watches:
                raise DirectoryNotWatchedError(f"Directory is not currently watched: {path}")

            watch = self._watches.pop(resolved_path)
            self._handlers.pop(resolved_path)

            if self._observer is not None:
                self._observer.unschedule(watch)

    def is_watching(self, path: Path | str) -> bool:
        """Checks if a directory path is actively watched.

        Args:
            path (Path | str): The directory path.

        Returns:
            bool: True if watched, False otherwise.
        """
        with self._lock:
            try:
                resolved_path = Path(path).resolve()
                return resolved_path in self._watches
            except (OSError, FileNotFoundError):
                return False

    def watched_directories(self) -> list[Path]:
        """Returns a sorted list of all active watched paths.

        Returns:
            list[Path]: Sorted active paths.
        """
        with self._lock:
            return sorted(list(self._watches.keys()))

    def get_event_store(self) -> EventStore:
        """Returns the shared EventStore instance.

        Returns:
            EventStore: Shared store.
        """
        return self._event_store

    def close(self) -> None:
        """Stops the observer and unschedules all directory watches.

        Safe to call multiple times.
        """
        with self._lock:
            if self._observer is not None:
                self._observer.stop()
                self._observer.join()
                self._observer = None

            self._watches.clear()
            self._handlers.clear()

    def __enter__(self) -> "WatchManager":
        return self

    def __exit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
        self.close()

    def __repr__(self) -> str:
        with self._lock:
            observer_running = self._observer is not None and self._observer.is_alive()
            return (
                f"WatchManager(watching={len(self._watches)}, "
                f"observer_running={observer_running})"
            )

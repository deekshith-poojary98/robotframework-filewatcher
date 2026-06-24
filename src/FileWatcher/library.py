import importlib.metadata
from robotlibcore import HybridCore
from FileWatcher.watcher import WatchManager
from FileWatcher.keywords.watching import WatchingKeywords
from FileWatcher.keywords.waiting import WaitingKeywords


class FileWatcher(HybridCore):
    """``FileWatcher`` is a modern Robot Framework library for filesystem monitoring.

    It uses ``watchdog`` to monitor directory changes in the background, collects
    events thread-safely in a non-consuming event store, and exposes keywords
    to wait for specific creation, modification, deletion, and stability states.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_AUTO_KEYWORDS = False

    try:
        ROBOT_LIBRARY_VERSION = importlib.metadata.version("robotframework-filewatcher")
    except importlib.metadata.PackageNotFoundError:
        ROBOT_LIBRARY_VERSION = "0.2.0"

    def __init__(self, max_events: int = 10000) -> None:
        """Initializes the FileWatcher library.

        `Args`:
        - max_events (int): The maximum number of historical events to retain.
        """
        self.watch_manager = WatchManager(max_events=int(max_events))
        libraries = [
            WatchingKeywords(self),
            WaitingKeywords(self),
        ]
        super().__init__(libraries)

    def close(self) -> None:
        """Cleans up and shuts down all active background observers.

        Called automatically by Robot Framework at the end of the execution.
        """
        self.watch_manager.close()

    def __enter__(self) -> "FileWatcher":
        return self

    def __exit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
        self.close()

    def __repr__(self) -> str:
        watching_count = len(self.watch_manager.watched_directories())
        return f"FileWatcher(version={self.ROBOT_LIBRARY_VERSION}, watching={watching_count})"

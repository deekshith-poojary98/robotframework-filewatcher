from pathlib import Path
from robot.api.deco import keyword
from FileWatcher.watcher import WatchManager


class WatchingKeywords:
    """Keywords for managing watched directories."""

    def __init__(self, ctx: any) -> None:
        """Initializes the WatchingKeywords component.

        Args:
            ctx: The parent FileWatcherLibrary context.
        """
        self.ctx = ctx

    @keyword("Start Watching Directory")
    def start_watching_directory(self, path: str, recursive: bool = True) -> None:
        """Start monitoring a directory for filesystem events.

        This keyword instructs the library to monitor the given directory
        and begin collecting filesystem events (create/modify/delete/move)
        into the internal EventStore. Observers run in the background
        so tests can continue while events are collected.

        Arguments:
            path: Directory path to monitor. Can be relative or absolute.
            recursive: If True (default), subdirectories are monitored too.

        Returns:
            None

        Raises:
            FileWatcherError: If the path is not a directory or observer fails to start.

        *Examples*
        | ***** Settings *****
        | Library    FileWatcher
        |
        | ***** Test Cases *****
        | Example
        |   Start Watching Directory    /path/to/watch    recursive=False
        """
        self.ctx.watch_manager.start_watch(path, recursive=recursive)

    @keyword("Stop Watching Directory")
    def stop_watching_directory(self, path: str) -> None:
        """Stop monitoring a previously watched directory.

        Arguments:
            path: Directory path that was previously started with
                `Start Watching Directory`. The path is resolved when
                matching active watchers to stop.

        Returns:
            None

        Raises:
            FileWatcherError: If there is no active watcher for the given path.

        *Examples*
        | ***** Settings *****
        | Library    FileWatcher
        |
        | ***** Test Cases *****
        | Example
        |   Start Watching Directory    ${DOWNLOADS}
        |   ${is_watching}=    Is Watching Directory    ${DOWNLOADS}
        |   Should Be True    ${is_watching}
        |   Stop Watching Directory    ${DOWNLOADS}
        """
        self.ctx.watch_manager.stop_watch(path)

    @keyword("Is Watching Directory")
    def is_watching_directory(self, path: str) -> bool:
        """Return whether the library currently monitors the given directory.

        Arguments:
            path: Directory path to check. Can be relative or absolute.

        Returns:
            bool: True if an active watcher exists for the resolved path,
            otherwise False.
        
        *Examples*
        | ***** Settings *****
        | Library    FileWatcher
        |
        | ***** Test Cases *****
        | Example
        |   Start Watching Directory    ${DOWNLOADS}
        |   ${is_watching}=    Is Watching Directory    ${DOWNLOADS}
        |   Should Be True    ${is_watching}
        """
        # Normalize the provided path before checking registry membership
        try:
            resolved = str(Path(path).resolve())
        except Exception:
            # Fall back to original value if resolution fails
            resolved = path
        return self.ctx.watch_manager.is_watching(resolved)

    @keyword("Get Watched Directories")
    def get_watched_directories(self) -> list[str]:
        """Return a sorted list of actively monitored directories.

        This returns absolute, unique paths for all directories currently
        being observed by the library (duplicates removed).

        Returns:
            list[str]: Sorted list of absolute paths.

        *Examples*
        | ***** Settings *****
        | Library    FileWatcher
        |
        | ***** Test Cases *****
        | Example
        |   ${dirs}=    Get Watched Directories
        |   Should Contain    ${dirs}    ${DOWNLOADS}
        """
        paths = self.ctx.watch_manager.watched_directories()
        # Ensure unique, sorted string representation
        seen = set()
        out = []
        for p in paths:
            s = str(p)
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

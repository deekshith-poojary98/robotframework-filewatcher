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
        """Starts watching the specified directory for filesystem events.

        Arguments:
            path: Path to the directory to watch.
            recursive: If True, subdirectories will also be watched.

        Examples:
        | Start Watching Directory | ${DOWNLOADS} |
        | Start Watching Directory | /path/to/watch | recursive=False |
        """
        self.ctx.watch_manager.start_watch(path, recursive=recursive)

    @keyword("Stop Watching Directory")
    def stop_watching_directory(self, path: str) -> None:
        """Stops watching the specified directory.

        Arguments:
            path: Path to the directory to stop watching.

        Examples:
        | Stop Watching Directory | ${DOWNLOADS} |
        """
        self.ctx.watch_manager.stop_watch(path)

    @keyword("Is Watching Directory")
    def is_watching_directory(self, path: str) -> bool:
        """Checks if the specified directory is actively monitored.

        Arguments:
            path: Path to the directory.

        Returns:
            True if watched, False otherwise.
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
        """Returns a sorted list of all actively monitored directories.

        Returns:
            A list of directory paths as strings.
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

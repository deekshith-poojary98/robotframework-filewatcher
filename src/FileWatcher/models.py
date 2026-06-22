from dataclasses import dataclass
from enum import Enum
import fnmatch
from pathlib import Path
import threading


class EventType(str, Enum):
    """Enumeration of file system event types."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass(frozen=True, slots=True)
class FileEvent:
    """Immutable representation of a file system event.

    Attributes:
        id (int): Monotonically increasing sequential ID.
        event_type (EventType): Type of event (created, modified, deleted, moved).
        src_path (Path): Path of the file/directory that triggered the event.
        dest_path (Path | None): Destination path for moved events. Defaults to None.
        watched_directory (Path): The root directory under watch that caught this event.
        timestamp (float): Epoch timestamp when the event was recorded.
    """

    id: int
    event_type: EventType
    src_path: Path
    watched_directory: Path
    timestamp: float
    dest_path: Path | None = None

    def matches_glob(self, pattern: str) -> bool:
        """Checks if the event's source or destination path matches the glob pattern.

        Matches against the path's filename (e.g. 'report.pdf') as well as the
        relative path from the watched directory (e.g. 'sub/report.pdf').

        Args:
            pattern (str): The glob pattern to match against (e.g. '*.pdf').

        Returns:
            bool: True if the pattern matches, False otherwise.
        """
        paths_to_check = [self.src_path]
        if self.dest_path is not None:
            paths_to_check.append(self.dest_path)

        for path in paths_to_check:
            # Match against filename (basename)
            if fnmatch.fnmatch(path.name, pattern):
                return True

            # Match against relative path from watched directory
            try:
                rel_path = path.relative_to(self.watched_directory)
                if fnmatch.fnmatch(str(rel_path), pattern) or fnmatch.fnmatch(
                    rel_path.as_posix(), pattern
                ):
                    return True
            except ValueError:
                # Path is not relative to watched_directory (should not normally happen)
                pass

        return False

    def matches_directory(self, directory: Path) -> bool:
        """Checks if the event path resides within or matches the given directory.

        Args:
            directory (Path): The directory path to check.

        Returns:
            bool: True if the path matches or is a descendant of the directory.
        """
        try:
            resolved_src = self.src_path.resolve()
            resolved_dir = directory.resolve()
            return resolved_dir == resolved_src or resolved_dir in resolved_src.parents
        except (ValueError, OSError):
            # Fallback to lexical comparison if resolution fails
            return directory == self.src_path or directory in self.src_path.parents

    def to_dict(self) -> dict:
        """Converts the FileEvent to a standard dictionary representation.

        Returns:
            dict: Dictionary containing serializable event data.
        """
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "src_path": str(self.src_path),
            "dest_path": str(self.dest_path) if self.dest_path is not None else None,
            "watched_directory": str(self.watched_directory),
            "timestamp": self.timestamp,
        }


class EventIdGenerator:
    """Thread-safe sequential generator for FileEvent IDs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = 0

    def next_id(self) -> int:
        """Generates the next sequential ID starting from 1.

        Returns:
            int: The next unique integer ID.
        """
        with self._lock:
            self._counter += 1
            return self._counter

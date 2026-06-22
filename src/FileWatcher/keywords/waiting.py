from pathlib import Path
import time
from robot.api.deco import keyword
from FileWatcher.exceptions import FileWatcherTimeoutError, FileWatcherError
from FileWatcher.models import EventType


class WaitingKeywords:
    """Keywords for waiting for file events and checking stability."""

    def __init__(self, ctx: any) -> None:
        """Initializes the WaitingKeywords component.

        Args:
            ctx: The parent FileWatcherLibrary context.
        """
        self.ctx = ctx

    @keyword("Wait For File Created")
    def wait_for_file_created(
        self, pattern: str | None = None, since_id: int = 0, timeout: float = 30.0
    ) -> dict:
        """Waits for a file creation event matching the pattern.

        Arguments:
            pattern: Glob pattern to filter files (e.g. '*.pdf').
            since_id: Match only events with ID greater than this value.
            timeout: Time in seconds to wait before failing.

        Returns a dictionary representation of the matching FileEvent.

        Examples:
        | ${event} = | Wait For File Created | *.pdf |
        | ${event} = | Wait For File Created | report.xlsx | since_id=12 | timeout=15 |
        """
        store = self.ctx.watch_manager.get_event_store()
        event = store.wait_for_event(
            event_type=EventType.CREATED,
            pattern=pattern,
            since_id=int(since_id),
            timeout=float(timeout),
        )
        return event.to_dict()

    @keyword("Wait For File Modified")
    def wait_for_file_modified(
        self, pattern: str | None = None, since_id: int = 0, timeout: float = 30.0
    ) -> dict:
        """Waits for a file modification event matching the pattern.

        Arguments:
            pattern: Glob pattern to filter files (e.g. '*.pdf').
            since_id: Match only events with ID greater than this value.
            timeout: Time in seconds to wait before failing.

        Returns a dictionary representation of the matching FileEvent.
        """
        store = self.ctx.watch_manager.get_event_store()
        event = store.wait_for_event(
            event_type=EventType.MODIFIED,
            pattern=pattern,
            since_id=int(since_id),
            timeout=float(timeout),
        )
        return event.to_dict()

    @keyword("Wait For File Deleted")
    def wait_for_file_deleted(
        self, pattern: str | None = None, since_id: int = 0, timeout: float = 30.0
    ) -> dict:
        """Waits for a file deletion event matching the pattern.

        Arguments:
            pattern: Glob pattern to filter files (e.g. '*.pdf').
            since_id: Match only events with ID greater than this value.
            timeout: Time in seconds to wait before failing.

        Returns a dictionary representation of the matching FileEvent.
        """
        store = self.ctx.watch_manager.get_event_store()
        event = store.wait_for_event(
            event_type=EventType.DELETED,
            pattern=pattern,
            since_id=int(since_id),
            timeout=float(timeout),
        )
        return event.to_dict()

    @keyword("Wait Until File Stable")
    def wait_until_file_stable(
        self, pattern: str, stability_time: float = 2.0, timeout: float = 30.0
    ) -> dict:
        """Waits for a file to be stable (no new events and file size remains constant).

        Resolves the file path in the following order:
        1. EventStore-first: Scan recorded events in memory.
        2. Filesystem-second: Scan watched directories on disk.
        3. Block/wait for a new event matching the pattern.

        Arguments:
            pattern: Glob pattern matching the file to wait for.
            stability_time: Duration in seconds the file must remain unchanged to be stable.
            timeout: Maximum wait time in seconds before failing.

        Returns:
            dict: Dictionary representation of the stable event.
        """
        stability_time = float(stability_time)
        timeout = float(timeout)
        deadline = time.time() + timeout
        store = self.ctx.watch_manager.get_event_store()

        matched_path: Path | None = None

        # 1. EventStore-first: Check recorded history for any events matching the pattern
        matching_events = [
            e for e in store.get_all() if e.matches_glob(pattern)
        ]
        if matching_events:
            latest_event = matching_events[-1]
            matched_path = (
                latest_event.src_path
                if latest_event.event_type != EventType.MOVED
                else latest_event.dest_path
            )

        # 2. Filesystem-second: Scan watched directories on disk
        if matched_path is None:
            for watched_dir in self.ctx.watch_manager.watched_directories():
                try:
                    for p in watched_dir.rglob(pattern):
                        if p.is_file():
                            matched_path = p
                            break
                except Exception:
                    pass
                if matched_path is not None:
                    break

        # 3. Block and wait for a new event to arrive if not resolved
        if matched_path is None:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise FileWatcherTimeoutError(
                    f"Timed out waiting for file matching pattern '{pattern}' to exist."
                )
            event = store.wait_for_event(pattern=pattern, timeout=remaining)
            matched_path = (
                event.src_path if event.event_type != EventType.MOVED else event.dest_path
            )
            assert matched_path is not None

        # 4. Once path is resolved, verify stability
        last_check_time = time.time()
        last_size = None
        if matched_path.exists():
            last_size = matched_path.stat().st_size

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise FileWatcherTimeoutError(
                    f"Timed out waiting for file '{matched_path}' to stabilize."
                )

            # Sleep for stability_time or remaining time
            sleep_time = min(stability_time, remaining)
            time.sleep(sleep_time)

            if not matched_path.exists():
                raise FileWatcherTimeoutError(
                    f"File '{matched_path}' was deleted or does not exist during stability check."
                )

            current_size = matched_path.stat().st_size

            # Check if any new events were recorded for this file
            new_events = [
                e
                for e in store.get_all()
                if e.timestamp > last_check_time
                and (e.src_path == matched_path or e.dest_path == matched_path)
                and e.event_type
                in (EventType.MODIFIED, EventType.MOVED, EventType.CREATED)
            ]

            if len(new_events) > 0 or current_size != last_size:
                # File is still active. Reset timer.
                last_size = current_size
                last_check_time = time.time()
                continue

            # No changes during the interval. It is stable!
            # Find the last matching event in the store to return
            all_file_events = [
                e
                for e in store.get_all()
                if (e.src_path == matched_path or e.dest_path == matched_path)
            ]
            if all_file_events:
                return all_file_events[-1].to_dict()
            else:
                # Fallback dictionary if it existed pre-watch and no events are recorded
                return {
                    "id": 0,
                    "event_type": "stable",
                    "src_path": str(matched_path),
                    "dest_path": None,
                    "watched_directory": "",
                    "timestamp": time.time(),
                }

    @keyword("Get File Events")
    def get_file_events(self) -> list[dict]:
        """Returns all events currently stored in the EventStore.

        Examples:
        | ${events} = | Get File Events |
        """
        store = self.ctx.watch_manager.get_event_store()
        return [e.to_dict() for e in store.get_all()]

    @keyword("Get File Events Since")
    def get_file_events_since(self, event_id: int) -> list[dict]:
        """Returns all events in the EventStore with ID greater than event_id.

        Examples:
        | ${new_events} = | Get File Events Since | 42 |
        """
        store = self.ctx.watch_manager.get_event_store()
        return [e.to_dict() for e in store.get_since(int(event_id))]

    @keyword("Clear Event History")
    def clear_event_history(self) -> None:
        """Clears all events currently retained in the EventStore.

        Examples:
        | Clear Event History |
        """
        store = self.ctx.watch_manager.get_event_store()
        store.clear()

    # Commenting this keyword for now since it has a few issues
    # @keyword("Wait For Download")
    def _wait_for_download(
        self, pattern: str, stability_time: float = 2.0, timeout: float = 30.0
    ) -> dict:
        """Waits for a file download to complete by waiting for the file to stabilize.

        Alias for 'Wait Until File Stable'.

        Arguments:
            pattern: Glob pattern matching the file to wait for (e.g. '*.pdf').
            stability_time: Duration in seconds the file must remain unchanged.
            timeout: Maximum wait time in seconds.

        Returns:
            dict: Dictionary representation of the event.
        """
        return self.wait_until_file_stable(pattern, stability_time, timeout)

    @keyword("Wait Until Directory Is Not Empty")
    def wait_until_directory_is_not_empty(
        self, path: str | Path, timeout: float = 30.0
    ) -> None:
        """Blocks until the specified directory contains at least one entry.

        Arguments:
            path: Directory path to watch.
            timeout: Time in seconds to wait before failing.
        """
        resolved_path = Path(path).resolve()
        if not resolved_path.exists() or not resolved_path.is_dir():
            raise FileWatcherError(f"Directory does not exist: {path}")

        deadline = time.time() + float(timeout)
        while True:
            if any(resolved_path.iterdir()):
                return
            if time.time() >= deadline:
                raise FileWatcherTimeoutError(
                    f"Timed out waiting for directory '{resolved_path}' to become non-empty."
                )
            time.sleep(0.2)

    @keyword("Wait Until File Count Is")
    def wait_until_file_count_is(
        self,
        path: str | Path,
        count: int,
        pattern: str = "*",
        timeout: float = 30.0,
    ) -> bool:
        """Blocks until the number of files matching pattern equals the target count.

        Arguments:
            path: Directory path to scan.
            count: Number of matching files expected.
            pattern: Glob pattern to count. Defaults to '*'.
            timeout: Time in seconds to wait before failing.

        Returns:
            bool: True when count matches.
        """
        resolved_path = Path(path).resolve()
        if not resolved_path.exists() or not resolved_path.is_dir():
            raise FileWatcherError(f"Directory does not exist: {path}")

        deadline = time.time() + float(timeout)
        while True:
            current_count = len(list(resolved_path.glob(pattern)))
            if current_count == int(count):
                return True
            if time.time() >= deadline:
                raise FileWatcherTimeoutError(
                    f"Timed out waiting for {count} files matching '{pattern}' in '{resolved_path}'."
                )
            time.sleep(0.2)

    @keyword("Find Files Matching Pattern")
    def find_files_matching_pattern(
        self, pattern: str, recursive: bool = True
    ) -> list[str]:
        """Searches all watched directories for files matching the pattern.

        Arguments:
            pattern: Glob pattern to search for.
            recursive: Whether to search recursively.

        Returns:
            list[str]: Sorted unique absolute file paths.
        """
        wm = self.ctx.watch_manager
        files: list[str] = []
        seen: set[str] = set()

        with wm._lock:
            for watched_dir in wm.watched_directories():
                try:
                    iterator = (
                        watched_dir.rglob(pattern)
                        if recursive
                        else watched_dir.glob(pattern)
                    )
                    for p in iterator:
                        if p.is_file():
                            absolute_path = str(p.resolve())
                            if absolute_path not in seen:
                                seen.add(absolute_path)
                                files.append(absolute_path)
                except Exception:
                    pass

        return sorted(files)

    @keyword("Get File Count")
    def get_file_count(
        self, pattern: str = "*", recursive: bool = True
    ) -> int:
        """Returns the number of files matching the pattern in watched directories.

        Arguments:
            pattern: Glob pattern to count. Defaults to '*'.
            recursive: Whether to search recursively. Defaults to True.

        Returns:
            int: Number of matching files.
        """
        return len(self.find_files_matching_pattern(pattern, recursive))

    @keyword("Get Current Event Id")
    def get_current_event_id(self) -> int:
        """Returns the ID of the latest event in the EventStore.

        Returns:
            int: The maximum event ID currently stored, or 0 if empty.
        """
        store = self.ctx.watch_manager.get_event_store()
        return store.get_current_event_id()

    @keyword("Get Latest File")
    def get_latest_file(self, pattern: str | None = None, limit: int = 1) -> str | list[str]:
        """Searches all watched directories for files matching the pattern.

        Sorts them by modification time descending and returns the latest file(s).

        Arguments:
            pattern: Glob pattern to filter files (e.g. '*.pdf').
            limit: Maximum number of files to return.

        Returns:
            str | list[str]: A single string path or a list of string paths.
        """
        limit = int(limit)
        glob_pattern = pattern if pattern else "*"
        wm = self.ctx.watch_manager
        files_found = []

        with wm._lock:
            for resolved_path, watch in wm._watches.items():
                is_recursive = watch.is_recursive
                try:
                    generator = resolved_path.rglob(glob_pattern) if is_recursive else resolved_path.glob(glob_pattern)
                    for p in generator:
                        try:
                            if p.is_file():
                                mtime = p.stat().st_mtime
                                files_found.append((p, mtime))
                        except (OSError, FileNotFoundError):
                            pass
                except Exception:
                    pass

        if not files_found:
            raise FileWatcherError(
                f"No files matching pattern '{glob_pattern}' found in watched directories."
            )

        # Sort descending by mtime
        files_found.sort(key=lambda x: x[1], reverse=True)
        str_paths = [str(item[0]) for item in files_found]

        if limit == 1:
            return str_paths[0]
        else:
            return str_paths[:limit]

    @keyword("Should Have File Event")
    def should_have_file_event(self, event_type: str | None = None, pattern: str | None = None) -> None:
        """Asserts that at least one matching event exists in the EventStore.

        Fails with AssertionError if no match is found.
        """
        store = self.ctx.watch_manager.get_event_store()
        events = store.get_all()

        target_type = None
        if event_type is not None:
            try:
                target_type = EventType(event_type.lower())
            except ValueError:
                pass

        for event in events:
            if target_type is not None and event.event_type != target_type:
                continue
            if pattern is not None and not event.matches_glob(pattern):
                continue
            return

        raise AssertionError(
            f"Assertion Failed: No event matching (event_type={event_type}, pattern={pattern}) "
            f"was found in the EventStore history (total events: {len(events)})."
        )

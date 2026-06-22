from pathlib import Path
import tempfile
import time
import pytest
from FileWatcher.exceptions import (
    DirectoryAlreadyWatchedError,
    DirectoryNotWatchedError,
    FileWatcherError,
)
from FileWatcher.watcher import WatchManager


def test_watch_manager_invalid_path() -> None:
    """Verify that start_watch raises FileWatcherError on invalid paths."""
    with WatchManager() as wm:
        # Non-existing path
        with pytest.raises(FileWatcherError) as exc:
            wm.start_watch("/non_existing/directory_path/foo/bar")
        assert "Path does not exist" in str(exc.value)

        # Path that is a file, not a directory
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(FileWatcherError) as exc:
                wm.start_watch(tmp_file.name)
            assert "Path is not a directory" in str(exc.value)


def test_watch_manager_lifecycle_and_duplicates() -> None:
    """Verify start, duplicate prevention, and stop lifecycle."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir).resolve()
        with WatchManager() as wm:
            assert len(wm.watched_directories()) == 0
            assert wm.is_watching(path) is False

            # Start watching
            wm.start_watch(path)
            assert wm.is_watching(path) is True
            assert wm.watched_directories() == [path]

            # Duplicate start should fail
            with pytest.raises(DirectoryAlreadyWatchedError):
                wm.start_watch(path)

            # Stop watching
            wm.stop_watch(path)
            assert wm.is_watching(path) is False
            assert len(wm.watched_directories()) == 0

            # Stopping again should raise error
            with pytest.raises(DirectoryNotWatchedError):
                wm.stop_watch(path)


def test_watch_manager_multiple_directories() -> None:
    """Verify managing multiple watched directories concurrently."""
    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        p1 = Path(dir1).resolve()
        p2 = Path(dir2).resolve()

        with WatchManager() as wm:
            wm.start_watch(p1)
            wm.start_watch(p2)

            assert wm.watched_directories() == sorted([p1, p2])
            assert wm.is_watching(p1) is True
            assert wm.is_watching(p2) is True

            wm.stop_watch(p1)
            assert wm.is_watching(p1) is False
            assert wm.is_watching(p2) is True
            assert wm.watched_directories() == [p2]


def test_watch_manager_event_delivery() -> None:
    """Verify raw OS filesystem events propagate to the EventStore through WatchManager."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        watch_path = Path(tmp_dir).resolve()
        with WatchManager() as wm:
            wm.start_watch(watch_path, recursive=False)
            store = wm.get_event_store()

            assert len(store) == 0

            # Write a file to trigger created/modified events
            test_file = watch_path / "test_event.txt"
            test_file.write_text("hello event")

            # Allow event thread loop to run and write to EventStore
            # Wait with timeout for the event to land
            try:
                matched_event = store.wait_for_event(
                    pattern="test_event.txt", timeout=2.0
                )
                assert matched_event.src_path.name == "test_event.txt"
                assert matched_event.watched_directory == watch_path
                assert matched_event.id >= 1
            except Exception as ex:
                pytest.fail(f"Event failed to propagate: {ex}")


def test_watch_manager_close_and_recreate_observer() -> None:
    """Verify close teardown and subsequent re-start logic."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir).resolve()
        wm = WatchManager()
        try:
            wm.start_watch(path)
            assert wm.is_watching(path) is True
            assert wm._observer is not None
            assert wm._observer.is_alive() is True

            # Close it
            wm.close()
            assert wm.is_watching(path) is False
            assert wm._observer is None

            # Starting watch again on a closed manager should work (recreates observer thread)
            wm.start_watch(path)
            assert wm.is_watching(path) is True
            assert wm._observer is not None
            assert wm._observer.is_alive() is True
        finally:
            wm.close()

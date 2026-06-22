import tempfile
import time
from pathlib import Path
import pytest
from FileWatcher.library import FileWatcher
from FileWatcher.exceptions import FileWatcherError
from FileWatcher.models import EventType, FileEvent


def test_get_current_event_id() -> None:
    """Verify Get Current Event Id keyword."""
    with FileWatcher() as lib:
        # Empty case
        assert lib.get_current_event_id() == 0

        # Push an event
        store = lib.watch_manager.get_event_store()
        event = FileEvent(
            id=42,
            event_type=EventType.CREATED,
            src_path=Path("/tmp/foo.txt"),
            watched_directory=Path("/tmp"),
            timestamp=time.time(),
        )
        store.push(event)
        assert lib.get_current_event_id() == 42


def test_watching_and_retrieving_directories() -> None:
    """Verify Is Watching Directory and Get Watched Directories."""
    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        p1 = Path(dir1).resolve()
        p2 = Path(dir2).resolve()

        with FileWatcher() as lib:
            # Initially empty
            assert lib.is_watching_directory(str(p1)) is False
            assert lib.get_watched_directories() == []

            # Watch p1
            lib.start_watching_directory(str(p1))
            assert lib.is_watching_directory(str(p1)) is True
            assert lib.is_watching_directory(str(p2)) is False
            assert lib.get_watched_directories() == [str(p1)]

            # Watch p2
            lib.start_watching_directory(str(p2))
            assert lib.get_watched_directories() == sorted([str(p1), str(p2)])

            # Stop watching p1
            lib.stop_watching_directory(str(p1))
            assert lib.is_watching_directory(str(p1)) is False
            assert lib.get_watched_directories() == [str(p2)]


def test_get_latest_file() -> None:
    """Verify Get Latest File keyword and options."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        watch_path = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(str(watch_path))

            # Empty case: should raise FileWatcherError
            with pytest.raises(FileWatcherError) as exc_info:
                lib.get_latest_file()
            assert "No files matching pattern" in str(exc_info.value)

            # Create file 1
            f1 = watch_path / "a.txt"
            f1.write_text("file A")
            # Ensure different timestamps by sleeping slightly or manually modifying st_mtime
            time.sleep(0.01)

            # Create file 2 (newer)
            f2 = watch_path / "b.pdf"
            f2.write_text("file B")
            time.sleep(0.01)

            # Create file 3 (newest)
            f3 = watch_path / "c.txt"
            f3.write_text("file C")

            # Get latest file (limit=1)
            latest = lib.get_latest_file()
            assert latest == str(f3)

            # Get latest with limit=2 (sorted descending by mtime)
            latest_2 = lib.get_latest_file(limit=2)
            assert latest_2 == [str(f3), str(f2)]

            # Get latest with pattern (limit=1)
            latest_pdf = lib.get_latest_file(pattern="*.pdf")
            assert latest_pdf == str(f2)

            # Get latest with limit=5 (all files)
            latest_all = lib.get_latest_file(limit=5)
            assert len(latest_all) == 3
            assert latest_all == [str(f3), str(f2), str(f1)]


def test_should_have_file_event() -> None:
    """Verify Should Have File Event keyword assertions."""
    with FileWatcher() as lib:
        # Empty case: should raise AssertionError
        with pytest.raises(AssertionError) as exc_info:
            lib.should_have_file_event(event_type="created", pattern="*.txt")
        assert "No event matching" in str(exc_info.value)

        # Push matching event
        store = lib.watch_manager.get_event_store()
        event = FileEvent(
            id=1,
            event_type=EventType.CREATED,
            src_path=Path("/tmp/data.json"),
            watched_directory=Path("/tmp"),
            timestamp=time.time(),
        )
        store.push(event)

        # Should pass
        lib.should_have_file_event(event_type="created", pattern="*.json")
        lib.should_have_file_event(event_type="created")
        lib.should_have_file_event(pattern="data.json")

        # Wrong type: should fail
        with pytest.raises(AssertionError):
            lib.should_have_file_event(event_type="deleted")

        # Wrong pattern: should fail
        with pytest.raises(AssertionError):
            lib.should_have_file_event(pattern="*.xlsx")

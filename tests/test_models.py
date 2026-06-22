from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
import time
import pytest
from FileWatcher.models import EventType, FileEvent, EventIdGenerator


def test_event_type_values() -> None:
    """Verify enum members and values."""
    assert EventType.CREATED == "created"
    assert EventType.MODIFIED == "modified"
    assert EventType.DELETED == "deleted"
    assert EventType.MOVED == "moved"


def test_file_event_immutability() -> None:
    """Verify that FileEvent properties are immutable."""
    event = FileEvent(
        id=1,
        event_type=EventType.CREATED,
        src_path=Path("/tmp/foo.txt"),
        watched_directory=Path("/tmp"),
        timestamp=time.time(),
    )
    with pytest.raises(FrozenInstanceError):
        # Trying to mutate frozen dataclass attribute should raise error
        event.id = 2  # type: ignore[misc]


def test_file_event_glob_matching() -> None:
    """Verify that matches_glob correctly matches various patterns."""
    event = FileEvent(
        id=1,
        event_type=EventType.CREATED,
        src_path=Path("/tmp/downloads/report.pdf"),
        watched_directory=Path("/tmp/downloads"),
        timestamp=time.time(),
    )

    # Basename matches
    assert event.matches_glob("*.pdf") is True
    assert event.matches_glob("report.*") is True
    assert event.matches_glob("report.pdf") is True
    assert event.matches_glob("*.xlsx") is False

    # Relative path matches
    event_sub = FileEvent(
        id=2,
        event_type=EventType.CREATED,
        src_path=Path("/tmp/downloads/sub/invoice_123.xlsx"),
        watched_directory=Path("/tmp/downloads"),
        timestamp=time.time(),
    )
    assert event_sub.matches_glob("sub/*.xlsx") is True
    assert event_sub.matches_glob("*.xlsx") is True  # Matches base name
    assert event_sub.matches_glob("sub/invoice_*.xlsx") is True
    assert event_sub.matches_glob("invoice_*.xlsx") is True
    assert event_sub.matches_glob("invoice_123.xlsx") is True
    assert event_sub.matches_glob("sub/report.pdf") is False


def test_file_event_glob_matching_moved() -> None:
    """Verify glob matches dest_path for MOVED events."""
    event = FileEvent(
        id=1,
        event_type=EventType.MOVED,
        src_path=Path("/tmp/downloads/old_report.pdf"),
        dest_path=Path("/tmp/downloads/new_report.pdf"),
        watched_directory=Path("/tmp/downloads"),
        timestamp=time.time(),
    )
    assert event.matches_glob("new_report.pdf") is True
    assert event.matches_glob("old_report.pdf") is True


def test_file_event_matches_directory() -> None:
    """Verify matches_directory behavior."""
    watched = Path("/tmp/downloads")
    event = FileEvent(
        id=1,
        event_type=EventType.CREATED,
        src_path=Path("/tmp/downloads/sub/file.txt"),
        watched_directory=watched,
        timestamp=time.time(),
    )

    assert event.matches_directory(watched) is True
    assert event.matches_directory(Path("/tmp/downloads/sub")) is True
    assert event.matches_directory(Path("/tmp/downloads/other")) is False


def test_file_event_to_dict() -> None:
    """Verify serialization to dictionary."""
    ts = time.time()
    event = FileEvent(
        id=10,
        event_type=EventType.CREATED,
        src_path=Path("/tmp/foo.txt"),
        watched_directory=Path("/tmp"),
        timestamp=ts,
    )
    expected = {
        "id": 10,
        "event_type": "created",
        "src_path": "/tmp/foo.txt",
        "dest_path": None,
        "watched_directory": "/tmp",
        "timestamp": ts,
    }
    assert event.to_dict() == expected


def test_event_id_generator_sequential() -> None:
    """Verify sequential id generation starting from 1."""
    generator = EventIdGenerator()
    assert generator.next_id() == 1
    assert generator.next_id() == 2
    assert generator.next_id() == 3


def test_event_id_generator_thread_safety() -> None:
    """Verify thread-safe generation without duplicate IDs."""
    generator = EventIdGenerator()
    num_threads = 50
    calls_per_thread = 100

    def generate_ids() -> list[int]:
        return [generator.next_id() for _ in range(calls_per_thread)]

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(generate_ids) for _ in range(num_threads)]
        results = []
        for f in futures:
            results.extend(f.result())

    # We expect total of num_threads * calls_per_thread IDs
    total_expected = num_threads * calls_per_thread
    assert len(results) == total_expected
    # Set of generated IDs should have exact length and max element should match
    assert len(set(results)) == total_expected
    assert min(results) == 1
    assert max(results) == total_expected

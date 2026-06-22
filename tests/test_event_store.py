from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time
import pytest
from FileWatcher.exceptions import FileWatcherTimeoutError
from FileWatcher.models import EventType, FileEvent
from FileWatcher.watcher import EventStore


def make_event(event_id: int, name: str, event_type: EventType = EventType.CREATED) -> FileEvent:
    return FileEvent(
        id=event_id,
        event_type=event_type,
        src_path=Path(f"/tmp/downloads/{name}"),
        watched_directory=Path("/tmp/downloads"),
        timestamp=time.time(),
    )


def test_event_store_push_and_get_all() -> None:
    """Verify push appends and get_all retrieves copy."""
    store = EventStore(max_events=10)
    assert len(store) == 0
    assert repr(store) == "EventStore(events=0, max_events=10)"

    e1 = make_event(1, "a.pdf")
    e2 = make_event(2, "b.xlsx")
    store.push(e1)
    store.push(e2)

    assert len(store) == 2
    assert repr(store) == "EventStore(events=2, max_events=10)"

    all_events = store.get_all()
    assert all_events == [e1, e2]
    # Check that all_events is a new list and modifying it does not affect store
    all_events.append(make_event(3, "c.txt"))
    assert len(store) == 2


def test_event_store_get_since_and_current_id() -> None:
    """Verify get_since returns events with ID > since_id and get_current_event_id behaves correctly."""
    store = EventStore(max_events=50)
    assert store.get_current_event_id() == 0

    e1 = make_event(10, "a.pdf")
    e2 = make_event(11, "b.xlsx")
    e3 = make_event(12, "c.txt")

    store.push(e1)
    store.push(e2)
    store.push(e3)

    assert store.get_current_event_id() == 12
    assert store.get_since(10) == [e2, e3]
    assert store.get_since(11) == [e3]
    assert store.get_since(12) == []
    assert store.get_since(5) == [e1, e2, e3]


def test_event_store_clear() -> None:
    """Verify clear removes all elements."""
    store = EventStore(max_events=10)
    store.push(make_event(1, "a.txt"))
    store.push(make_event(2, "b.txt"))
    assert len(store) == 2

    store.clear()
    assert len(store) == 0
    assert store.get_all() == []
    assert store.get_current_event_id() == 0


def test_event_store_maxlen() -> None:
    """Verify deque maxlen eviction behavior."""
    store = EventStore(max_events=3)
    e1 = make_event(1, "a.txt")
    e2 = make_event(2, "b.txt")
    e3 = make_event(3, "c.txt")
    e4 = make_event(4, "d.txt")

    store.push(e1)
    store.push(e2)
    store.push(e3)
    assert store.get_all() == [e1, e2, e3]

    store.push(e4)
    # Oldest (e1) should be evicted
    assert store.get_all() == [e2, e3, e4]
    assert len(store) == 3


def test_wait_for_event_immediate() -> None:
    """Verify wait_for_event returns immediately when event already exists in history."""
    store = EventStore()
    e = make_event(5, "report.pdf", EventType.CREATED)
    store.push(e)

    # Matches pattern and event_type
    matched = store.wait_for_event(event_type=EventType.CREATED, pattern="*.pdf", since_id=0, timeout=1.0)
    assert matched == e


def test_wait_for_event_delayed() -> None:
    """Verify wait_for_event blocks and returns when event is pushed dynamically."""
    store = EventStore()
    e = make_event(100, "report.pdf", EventType.CREATED)

    def push_later() -> None:
        time.sleep(0.1)
        store.push(e)

    t = threading.Thread(target=push_later)
    t.start()

    # Blocks until pushed
    matched = store.wait_for_event(pattern="*.pdf", timeout=2.0)
    assert matched == e
    t.join()


def test_wait_for_event_timeout() -> None:
    """Verify wait_for_event raises FileWatcherTimeoutError on timeout."""
    store = EventStore()
    with pytest.raises(FileWatcherTimeoutError) as exc_info:
        store.wait_for_event(pattern="*.pdf", timeout=0.1)
    assert "Timed out waiting for file event" in str(exc_info.value)


def test_multiple_concurrent_waiters() -> None:
    """Verify multiple threads waiting concurrently for different patterns all get their events."""
    store = EventStore()
    pdf_event = make_event(1, "invoice.pdf")
    xlsx_event = make_event(2, "data.xlsx")

    results = {}

    def wait_for_pdf() -> None:
        try:
            results["pdf"] = store.wait_for_event(pattern="*.pdf", timeout=2.0)
        except Exception as ex:
            results["pdf"] = ex

    def wait_for_xlsx() -> None:
        try:
            results["xlsx"] = store.wait_for_event(pattern="*.xlsx", timeout=2.0)
        except Exception as ex:
            results["xlsx"] = ex

    t1 = threading.Thread(target=wait_for_pdf)
    t2 = threading.Thread(target=wait_for_xlsx)

    t1.start()
    t2.start()

    time.sleep(0.1)
    # Push events
    store.push(pdf_event)
    store.push(xlsx_event)

    t1.join()
    t2.join()

    assert results["pdf"] == pdf_event
    assert results["xlsx"] == xlsx_event


def test_event_store_thread_safety() -> None:
    """Verify concurrent push operations keep consistency."""
    store = EventStore(max_events=1000)
    num_threads = 10
    events_per_thread = 50

    def worker(thread_idx: int) -> None:
        for i in range(events_per_thread):
            store.push(make_event(thread_idx * 100 + i, f"file_{thread_idx}_{i}.txt"))

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, idx) for idx in range(num_threads)]
        for f in futures:
            f.result()

    assert len(store) == num_threads * events_per_thread

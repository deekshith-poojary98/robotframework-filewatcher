import tempfile
from pathlib import Path
import pytest
from FileWatcher.library import FileWatcher
from FileWatcher.watcher import WatchManager


def test_library_version_and_metadata() -> None:
    """Verify version metadata on the library."""
    lib = FileWatcher()
    # Should be default fallback version or package version
    assert lib.ROBOT_LIBRARY_VERSION in ("0.1.0", "0.1.0")  # Or whatever package is installed as
    assert lib.ROBOT_LIBRARY_SCOPE == "GLOBAL"
    assert lib.ROBOT_AUTO_KEYWORDS is False


def test_library_keyword_registration() -> None:
    """Verify keyword discovery via HybridCore and keyword count."""
    lib = FileWatcher()
    keywords = lib.get_keyword_names()
    expected = [
        "Start Watching Directory",
        "Stop Watching Directory",
        "Wait For File Created",
        "Wait For File Modified",
        "Wait For File Deleted",
        "Wait Until File Stable",
        "Wait Until Directory Is Not Empty",
        "Wait Until File Count Is",
        "Find Files Matching Pattern",
        "Get File Count",
        "Get File Events",
        "Get File Events Since",
        "Clear Event History",
        "Is Watching Directory",
        "Get Watched Directories",
        "Get Current Event Id",
        "Get Latest File",
        "Should Have File Event",
    ]
    for kw in expected:
        assert kw in keywords

    # Validate that close, __repr__, etc. are NOT exposed as keywords
    assert "close" not in keywords
    assert "__repr__" not in keywords


def test_library_watch_manager_creation() -> None:
    """Verify WatchManager is instantiated correctly with matching configuration."""
    lib = FileWatcher(max_events=123)
    assert isinstance(lib.watch_manager, WatchManager)
    assert lib.watch_manager.get_event_store()._max_events == 123


def test_library_close_logic() -> None:
    """Verify close cleanly shuts down WatchManager."""
    lib = FileWatcher()
    with tempfile.TemporaryDirectory() as tmp_dir:
        lib.start_watching_directory(tmp_dir)
        assert len(lib.watch_manager.watched_directories()) == 1

        lib.close()
        assert len(lib.watch_manager.watched_directories()) == 0
        assert lib.watch_manager._observer is None


def test_library_context_manager() -> None:
    """Verify context manager interface calls close at exit."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with FileWatcher() as lib:
            lib.start_watching_directory(tmp_dir)
            assert len(lib.watch_manager.watched_directories()) == 1
            # Access active watch
            assert lib.watch_manager.is_watching(tmp_dir) is True

        # After exiting block, observer is closed and watches are cleared
        assert len(lib.watch_manager.watched_directories()) == 0


def test_library_repr() -> None:
    """Verify string representation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with FileWatcher() as lib:
            assert repr(lib) == f"FileWatcher(version={lib.ROBOT_LIBRARY_VERSION}, watching=0)"

            lib.start_watching_directory(tmp_dir)
            assert repr(lib) == f"FileWatcher(version={lib.ROBOT_LIBRARY_VERSION}, watching=1)"

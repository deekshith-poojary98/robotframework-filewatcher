import tempfile
import time
from pathlib import Path
import pytest
from FileWatcher.library import FileWatcher
from FileWatcher.exceptions import FileWatcherError, FileWatcherTimeoutError


def test_find_files_matching_pattern_empty_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with FileWatcher() as lib:
            lib.start_watching_directory(tmp_dir)
            files = lib.find_files_matching_pattern("*.pdf")
            assert files == []


def test_find_files_matching_pattern_recursive_and_duplicates() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir).resolve()
        nested = base / "nested"
        nested.mkdir()
        file_a = base / "a.pdf"
        file_b = nested / "b.pdf"
        file_a.write_text("a")
        file_b.write_text("b")

        with FileWatcher() as lib:
            lib.start_watching_directory(base)
            files = lib.find_files_matching_pattern("*.pdf", recursive=True)
            assert sorted(files) == sorted([str(file_a.resolve()), str(file_b.resolve())])

            non_recursive_files = lib.find_files_matching_pattern("*.pdf", recursive=False)
            assert non_recursive_files == [str(file_a.resolve())]

            # Duplicate test: symlink to the same file should not duplicate results
            symlink = base / "a_link.pdf"
            symlink.symlink_to(file_a)
            files_with_symlink = lib.find_files_matching_pattern("*.pdf", recursive=True)
            assert sorted(files_with_symlink) == sorted([str(file_a.resolve()), str(file_b.resolve())])


def test_get_file_count_returns_correct_count() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        (directory / "a.pdf").write_text("a")
        (directory / "b.pdf").write_text("b")
        (directory / "c.txt").write_text("c")

        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            assert lib.get_file_count("*.pdf") == 2
            assert lib.get_file_count("*.txt") == 1
            assert lib.get_file_count("*") == 3


def test_wait_until_file_count_is_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)

            def create_files() -> None:
                time.sleep(0.1)
                (directory / "a.pdf").write_text("a")
                time.sleep(0.1)
                (directory / "b.pdf").write_text("b")
                time.sleep(0.1)
                (directory / "c.pdf").write_text("c")

            from threading import Thread

            thread = Thread(target=create_files)
            thread.start()

            assert lib.wait_until_file_count_is(directory, count=3, pattern="*.pdf", timeout=5.0) is True
            thread.join()


def test_wait_until_file_count_is_timeout() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            with pytest.raises(FileWatcherTimeoutError):
                lib.wait_until_file_count_is(directory, count=1, pattern="*.pdf", timeout=0.2)


def test_wait_until_directory_is_not_empty_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)

            def create_file() -> None:
                time.sleep(0.1)
                (directory / "a.txt").write_text("hello")

            from threading import Thread

            thread = Thread(target=create_file)
            thread.start()

            lib.wait_until_directory_is_not_empty(directory, timeout=5.0)
            thread.join()


def test_wait_until_directory_is_not_empty_timeout() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            with pytest.raises(FileWatcherTimeoutError):
                lib.wait_until_directory_is_not_empty(directory, timeout=0.2)


def test_find_files_matching_pattern_nested_files() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir).resolve()
        subdir = base / "sub"
        subdir.mkdir()
        (subdir / "alpha.pdf").write_text("x")
        (subdir / "beta.pdf").write_text("y")
        with FileWatcher() as lib:
            lib.start_watching_directory(base)
            files = lib.find_files_matching_pattern("*.pdf", recursive=True)
            assert files == sorted([str((subdir / "alpha.pdf").resolve()), str((subdir / "beta.pdf").resolve())])


def test_find_files_matching_pattern_returns_absolute_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir).resolve()
        (base / "report.pdf").write_text("z")
        with FileWatcher() as lib:
            lib.start_watching_directory(base)
            files = lib.find_files_matching_pattern("*.pdf")
            assert files == [str((base / "report.pdf").resolve())]


def test_wait_until_directory_is_not_empty_immediate_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        (directory / "file.txt").write_text("hello")
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            lib.wait_until_directory_is_not_empty(directory, timeout=1.0)


def test_wait_until_directory_is_not_empty_invalid_path_raises_error() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        invalid_path = Path(tmp_dir) / "missing"
        with FileWatcher() as lib:
            lib.start_watching_directory(tmp_dir)
            with pytest.raises(FileWatcherError):
                lib.wait_until_directory_is_not_empty(invalid_path, timeout=0.5)


def test_wait_until_file_count_is_immediate_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        (directory / "a.pdf").write_text("a")
        (directory / "b.pdf").write_text("b")
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            assert lib.wait_until_file_count_is(directory, count=2, pattern="*.pdf", timeout=1.0) is True


def test_wait_until_file_count_is_invalid_path_raises_error() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        invalid_path = Path(tmp_dir) / "missing"
        with FileWatcher() as lib:
            lib.start_watching_directory(tmp_dir)
            with pytest.raises(FileWatcherError):
                lib.wait_until_file_count_is(invalid_path, count=1, pattern="*.pdf", timeout=0.5)


def test_find_files_matching_pattern_multiple_watched_directories() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir1, tempfile.TemporaryDirectory() as tmp_dir2:
        dir1 = Path(tmp_dir1).resolve()
        dir2 = Path(tmp_dir2).resolve()
        (dir1 / "a.pdf").write_text("1")
        (dir2 / "b.pdf").write_text("2")
        with FileWatcher() as lib:
            lib.start_watching_directory(dir1)
            lib.start_watching_directory(dir2)
            files = lib.find_files_matching_pattern("*.pdf")
            assert files == sorted([str((dir1 / "a.pdf").resolve()), str((dir2 / "b.pdf").resolve())])


def test_find_files_matching_pattern_excludes_directories() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir).resolve()
        (base / "a.pdf").write_text("a")
        sub = base / "subdir"
        sub.mkdir()
        (sub / "b.pdf").write_text("b")
        (base / "c_dir").mkdir()
        with FileWatcher() as lib:
            lib.start_watching_directory(base)
            files = lib.find_files_matching_pattern("*")
            assert str((base / "c_dir").resolve()) not in files
            assert str((base / "a.pdf").resolve()) in files
            assert str((sub / "b.pdf").resolve()) in files


def test_get_file_count_no_watched_directories_returns_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with FileWatcher() as lib:
            assert lib.get_file_count("*.pdf") == 0


def test_find_files_matching_pattern_sorted_alphabetically() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir).resolve()
        (base / "z.pdf").write_text("z")
        (base / "a.pdf").write_text("a")
        with FileWatcher() as lib:
            lib.start_watching_directory(base)
            files = lib.find_files_matching_pattern("*.pdf")
            assert files == [str((base / "a.pdf").resolve()), str((base / "z.pdf").resolve())]


def test_file_should_be_stable_assertion_wrapper() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            file_path = directory / "stable.txt"
            file_path.write_text("hello")
            lib.file_should_be_stable("stable.txt", stability_time=0.1)


def test_wait_until_file_does_not_exist_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            file_path = directory / "temp.lock"
            file_path.write_text("x")

            def remove_file() -> None:
                time.sleep(0.1)
                file_path.unlink()

            from threading import Thread

            thread = Thread(target=remove_file)
            thread.start()
            lib.wait_until_file_does_not_exist("temp.lock", timeout=5.0)
            thread.join()


def test_get_oldest_file_returns_oldest_path() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        older = directory / "older.txt"
        newer = directory / "newer.txt"
        older.write_text("a")
        time.sleep(0.1)
        newer.write_text("b")
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            assert lib.get_oldest_file("*.txt") == str(older.resolve())


def test_get_file_checksum_and_assertion() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        target = directory / "checksum.txt"
        target.write_text("abcd")
        with FileWatcher() as lib:
            actual = lib.get_file_checksum(str(target), algorithm="md5")
            assert actual == "e2fc714c4727ee9395f324cd2e7f331f"
            lib.file_checksum_should_be(str(target), actual, algorithm="md5")


def test_wait_for_any_file_event_and_statistics() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            file_path = directory / "any.txt"
            file_path.write_text("hello")
            event = lib.wait_for_any_file_event("any.txt", timeout=5.0)
            assert event["event_type"] in {"created", "modified"}

            stats = lib.get_event_statistics()
            assert stats["total"] >= 1
            assert stats["created"] >= 1


def test_wait_for_file_moved_returns_moved_event() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            src = directory / "source.txt"
            dest = directory / "dest.txt"
            src.write_text("moved")
            created = lib.wait_for_file_created("source.txt", timeout=5.0)
            src.rename(dest)
            event = lib.wait_for_file_moved("dest.txt", since_id=created["id"], timeout=5.0)
            assert event["event_type"] == "moved"
            assert event["src_path"].endswith("source.txt")
            assert event["dest_path"].endswith("dest.txt")


def test_wait_until_directory_is_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            target = directory / "temp.txt"
            target.write_text("data")

            def remove_file() -> None:
                time.sleep(0.1)
                target.unlink()

            from threading import Thread

            thread = Thread(target=remove_file)
            thread.start()
            lib.wait_until_directory_is_empty(directory, timeout=5.0)
            thread.join()


def test_wait_until_file_size_is_condition() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        file_path = directory / "big.txt"
        file_path.write_text("small")
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)

            def enlarge() -> None:
                time.sleep(0.1)
                file_path.write_text("x" * 200)

            from threading import Thread

            thread = Thread(target=enlarge)
            thread.start()
            lib.wait_until_file_size_is("*.txt", "> 100", timeout=5.0)
            thread.join()


def test_wait_until_file_checksum_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        target = directory / "checksum.txt"
        target.write_text("version1")
        with FileWatcher() as lib:
            old = lib.get_file_checksum(str(target), algorithm="sha256")

            def update() -> None:
                time.sleep(0.1)
                target.write_text("version2")

            from threading import Thread

            thread = Thread(target=update)
            thread.start()
            new = lib.wait_until_file_checksum_changes(str(target), old, timeout=5.0)
            assert new != old
            thread.join()


def test_get_new_and_deleted_files_since() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            checkpoint = lib.get_current_event_id()

            file_a = directory / "a.txt"
            file_b = directory / "b.txt"
            file_a.write_text("a")
            lib.wait_for_file_created("a.txt", timeout=5.0)
            file_b.write_text("b")
            lib.wait_for_file_created("b.txt", timeout=5.0)

            deleted = []

            def remove_a() -> None:
                time.sleep(0.1)
                file_a.unlink()

            from threading import Thread

            thread = Thread(target=remove_a)
            thread.start()
            lib.wait_for_file_deleted("a.txt", timeout=5.0)
            thread.join()

            new_files = lib.get_new_files_since(checkpoint)
            assert str(file_a) in new_files or str(file_b) in new_files
            assert str(file_b) in new_files

            deleted_files = lib.get_deleted_files_since(checkpoint)
            assert str(file_a) in deleted_files


def test_file_should_not_change() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir).resolve()
        target = directory / "stable.txt"
        target.write_text("unchanged")
        with FileWatcher() as lib:
            lib.start_watching_directory(directory)
            lib.file_should_not_change("stable.txt", duration=1.0)

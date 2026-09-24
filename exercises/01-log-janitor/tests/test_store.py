"""Contract for `LocalStore`."""

from __future__ import annotations

from logjanitor.store import LocalStore


def test_lists_files_recursively_with_relative_posix_keys(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "a.log").write_text("12345")
    (tmp_path / "nested" / "b.log").write_text("123")

    by_key = {a.key: a for a in LocalStore(tmp_path).list_artifacts()}

    assert set(by_key) == {"a.log", "nested/b.log"}
    assert by_key["a.log"].size_bytes == 5
    assert by_key["nested/b.log"].size_bytes == 3


def test_timestamps_are_timezone_aware(tmp_path):
    """Naive mtimes silently shift age calculations by your UTC offset."""
    (tmp_path / "a.log").write_text("x")
    (found,) = LocalStore(tmp_path).list_artifacts()
    assert found.modified_at.tzinfo is not None
    assert found.modified_at.utcoffset() is not None


def test_directories_are_not_artifacts(tmp_path):
    (tmp_path / "empty").mkdir()
    assert list(LocalStore(tmp_path).list_artifacts()) == []


def test_delete_removes_the_file(tmp_path):
    target = tmp_path / "a.log"
    target.write_text("x")
    store = LocalStore(tmp_path)

    (found,) = store.list_artifacts()
    store.delete(found)

    assert not target.exists()


def test_delete_is_idempotent(tmp_path):
    """Unattended tools get re-run. A crash on the second run is a page."""
    target = tmp_path / "a.log"
    target.write_text("x")
    store = LocalStore(tmp_path)
    (found,) = store.list_artifacts()

    store.delete(found)
    store.delete(found)

    assert not target.exists()

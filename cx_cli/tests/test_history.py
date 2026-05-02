from pathlib import Path

from cx_cli import history


def test_append_and_read(tmp_path: Path):
    p = tmp_path / "history"
    history.append("/a", 10, p)
    history.append("/b", 10, p)
    history.append("/c", 10, p)
    assert history.read(p) == ["/a", "/b", "/c"]


def test_append_dedups_consecutive(tmp_path: Path):
    p = tmp_path / "history"
    history.append("/a", 10, p)
    history.append("/a", 10, p)
    history.append("/b", 10, p)
    history.append("/a", 10, p)
    assert history.read(p) == ["/a", "/b", "/a"]


def test_trim(tmp_path: Path):
    p = tmp_path / "history"
    for i in range(20):
        history.append(f"/p{i}", 5, p)
    assert history.read(p) == [f"/p{i}" for i in range(15, 20)]


def test_previous(tmp_path: Path):
    p = tmp_path / "history"
    history.append("/a", 10, p)
    history.append("/b", 10, p)
    history.append("/c", 10, p)
    # Last is /c (current). Previous is /b.
    assert history.previous(p) == "/b"


def test_recent(tmp_path: Path):
    p = tmp_path / "history"
    for i in range(5):
        history.append(f"/p{i}", 100, p)
    # most recent first
    assert history.recent(3, p) == ["/p4", "/p3", "/p2"]

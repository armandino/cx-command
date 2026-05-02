"""Visited-dir history: append, read, trim."""
from __future__ import annotations

from pathlib import Path

HISTORY_PATH = Path.home() / ".cache" / "cx" / "history"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read(path: Path = HISTORY_PATH) -> list[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]


def append(entry: str, max_size: int,
           path: Path = HISTORY_PATH) -> None:
    if not entry:
        return
    _ensure_parent(path)
    lines = read(path)
    # Avoid consecutive duplicates so `cx -` toggles sensibly.
    if lines and lines[-1] == entry:
        return
    lines.append(entry)
    if len(lines) > max_size:
        lines = lines[-max_size:]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def previous(path: Path = HISTORY_PATH) -> str | None:
    """Return the second-to-last entry (the 'previous' dir)."""
    lines = read(path)
    if len(lines) >= 2:
        return lines[-2]
    if len(lines) == 1:
        return lines[0]
    return None


def recent(n: int, path: Path = HISTORY_PATH) -> list[str]:
    lines = read(path)
    return list(reversed(lines[-n:])) if n > 0 else []

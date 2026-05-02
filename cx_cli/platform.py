"""Platform helpers: Cygwin detection, cygpath translation, opener defaults."""
from __future__ import annotations

import functools
import platform as _platform
import shutil
import subprocess


@functools.lru_cache(maxsize=1)
def is_cygwin() -> bool:
    sysname = _platform.system()
    if sysname.startswith("CYGWIN"):
        return True
    return shutil.which("cygpath") is not None and sysname.lower() == "windows"


@functools.lru_cache(maxsize=1)
def is_linux() -> bool:
    return _platform.system() == "Linux" and not is_cygwin()


@functools.lru_cache(maxsize=256)
def cygpath_u(path: str) -> str:
    """Translate a (possibly Windows-style) path to a POSIX/Cygwin path."""
    if not is_cygwin() or not path:
        return path
    try:
        result = subprocess.run(
            ["cygpath", "-u", path],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.rstrip("\r\n") or path
    except (FileNotFoundError, subprocess.CalledProcessError):
        return path


@functools.lru_cache(maxsize=256)
def cygpath_w(path: str) -> str:
    """Translate a POSIX/Cygwin path to a Windows-style path."""
    if not is_cygwin() or not path:
        return path
    try:
        result = subprocess.run(
            ["cygpath", "-w", path],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.rstrip("\r\n") or path
    except (FileNotFoundError, subprocess.CalledProcessError):
        return path


def default_opener() -> str:
    """Default file-manager opener for the current platform."""
    if is_cygwin():
        return "explorer"
    if _platform.system() == "Darwin":
        return "open"
    return "xdg-open"

"""User-facing output + shell directives.

Directives are tab-delimited lines prefixed with __CX__ that are consumed by
the cx() shell wrapper in cx.sh. Only ONE directive is emitted per invocation
and it is always the last line of stdout. Directive lines are written as plain
text (no ANSI) so the wrapper's tab-splitting stays reliable.

Human-facing output is rendered via rich with a color theme, similar to the
`task` CLI. Because the shell wrapper captures stdout via $(), python's stdout
is not a TTY; we force_terminal=True so colors still reach the user's terminal
when the wrapper re-prints the body. Set NO_COLOR=1 (or CX_NO_COLOR=1) to
disable coloring.
"""
from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

DIRECTIVE_PREFIX = "__CX__"

_THEME = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "muted": "dim",
    "heading": "bold magenta",
    "letter": "bold cyan",
    "name": "bold",
    "path": "white",
    "unresolved": "red",
    "note": "yellow",
    "cmd": "cyan",
    "index": "dim cyan",
})


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CX_NO_COLOR"):
        return False
    return True


def _make_console(stderr: bool = False) -> Console:
    return Console(
        theme=_THEME,
        no_color=not _use_color(),
        force_terminal=_use_color(),
        highlight=False,
        soft_wrap=True,
        stderr=stderr,
    )


_out = _make_console(stderr=False)
_err = _make_console(stderr=True)


def console() -> Console:
    return _out


# ---------- directives (plain text, no styling) ----------

def emit(*parts: str) -> None:
    """Emit a directive as the final line of stdout."""
    line = "\t".join([DIRECTIVE_PREFIX, *parts])
    sys.stdout.write(line + "\n")


def cd(path: str) -> None:
    emit("CD", path)


def open_dir(tokens: list[str]) -> None:
    """Emit an OPEN directive. All tokens become argv for the opener process."""
    emit("OPEN", *tokens)


def exec_in(path: str, argv: list[str]) -> None:
    emit("EXEC", path, *argv)


# ---------- styled output ----------

def info(msg: str = "") -> None:
    """Plain informational line (may contain rich markup)."""
    _out.print(msg)


def success(msg: str) -> None:
    _out.print(f"[success]{msg}[/success]")


def warning(msg: str) -> None:
    _out.print(f"[warning]{msg}[/warning]")


def muted(msg: str) -> None:
    _out.print(f"[muted]{msg}[/muted]")


def heading(msg: str) -> None:
    _out.print(f"[heading]{msg}[/heading]")


def note(msg: str) -> None:
    _out.print(f"  [muted]note:[/muted] [note]{msg}[/note]")


def error(msg: str) -> None:
    from rich.markup import escape
    _err.print(f"[error]cx:[/error] {escape(msg)}")


def table(**kwargs) -> Table:
    """Return a rich Table styled for cx output (no box, compact padding)."""
    defaults = dict(show_header=False, box=None, padding=(0, 1), pad_edge=False)
    defaults.update(kwargs)
    return Table(**defaults)


def print_table(t: Table) -> None:
    _out.print(t)

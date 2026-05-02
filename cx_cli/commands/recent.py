"""`cx recent [N]` — show last N visited dirs (default 10)."""
from __future__ import annotations

from rich.text import Text

from .. import history, output
from ..config import Config


def run(_config: Config, n_arg: str | None) -> int:
    n = 10
    if n_arg is not None:
        try:
            n = int(n_arg)
        except ValueError:
            output.error(f"recent: expected integer, got '{n_arg}'")
            return 1
        if n <= 0:
            output.error("recent: N must be > 0")
            return 1
    items = history.recent(n)
    if not items:
        output.muted("(no history)")
        return 0
    t = output.table()
    t.add_column(justify="right")
    t.add_column()
    for i, entry in enumerate(items, 1):
        t.add_row(Text(str(i), style="index"), Text(entry, style="path"))
    output.print_table(t)
    return 0

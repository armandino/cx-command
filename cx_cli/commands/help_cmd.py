"""`cx help` — usage text."""
from __future__ import annotations

from rich.text import Text

from .. import output

_USAGE = [
    ("cx", "List all aliases (letter, name, resolved path)"),
    ("cx <name>", "cd to alias"),
    ("cx <letter>", "cd to alias by auto-assigned letter (a, b, c, ...)"),
    ("cx <name>/sub/path", "cd to alias joined with sub-path"),
    ("cx -", "cd to previous cx dir"),
    ("cx help [<subcommand>]", "Show help"),
]

_SUBCOMMANDS = [
    ("cx add <name> <path> [-g <group>]", "Add alias (default group: 'default')"),
    ("cx rm <name>", "Remove alias"),
    ("cx edit", "Open ~/.cxrc.toml in $EDITOR"),
    ("cx init <shell>", "Print shell integration code (eval to activate)"),
    ("cx which <name>[/sub]", "Print resolved path (scriptable)"),
    ("cx recent [N]", "Show last N visited dirs (default 10)"),
    ("cx open [<name>[/sub]] [-w <opener>]", "Open with configured opener (no arg = cwd)"),
    ("cx ls <name>[/sub] [-- ls-args]", "Run ls in resolved dir"),
    ("cx exec <name>[/sub] -- cmd args", "Run command in resolved dir without cd-ing"),
]

_CONFIG = [
    ("~/.cxrc.toml", "Aliases + settings (paths support ${VAR}, ~, relative)"),
    ("~/.cache/cx/history", "Visited-dir history"),
]

_EXAMPLES = [
    "cx add foo /path/to/foo",
    "cx add bar ~/projects/bar --group projects",
    "cx bar/src",
    'cd "$(cx which bar)/bar-sub-dir"',
    "cx exec bar -- git status",
]


def _render_section(title: str, rows: list[tuple[str, str]]) -> None:
    output.heading(title)
    t = output.table()
    t.add_column(no_wrap=True)
    t.add_column()
    for cmd, desc in rows:
        t.add_row(Text("  " + cmd, style="cmd"), Text(desc, style="muted"))
    output.print_table(t)


def run(_args: list[str] | None = None) -> int:
    output.heading("cx — directory navigation by alias")
    output.info("")
    _render_section("USAGE", _USAGE + [("", "")] + _SUBCOMMANDS)
    output.info("")
    _render_section("CONFIG", _CONFIG)
    output.info("")
    output.heading("EXAMPLES")
    for ex in _EXAMPLES:
        output.console().print(Text("  " + ex, style="cmd"))
    return 0

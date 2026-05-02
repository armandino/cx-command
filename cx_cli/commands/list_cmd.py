"""`cx` — list aliases as grouped tables."""
from __future__ import annotations

from rich.text import Text

from .. import output, resolver
from ..config import Config, DEFAULT_GROUP


def _render_group(config: Config, group: str, aliases: list) -> None:
    label = "(default)" if group == DEFAULT_GROUP else group
    output.heading(label)
    t = output.table()
    t.add_column(justify="right")
    t.add_column()
    t.add_column()
    for a in aliases:
        try:
            r = resolver.resolve(config, a.name)
            path_cell = Text(r.path, style="path")
        except resolver.ResolveError as e:
            path_cell = Text(f"<unresolved: {e}>", style="unresolved")
        t.add_row(
            Text(a.letter, style="letter"),
            Text(a.name, style="name"),
            path_cell,
        )
    output.print_table(t)


def run(config: Config) -> int:
    if not config.aliases:
        output.info("no aliases defined. Add one with: [cmd]cx add <name> <path>[/cmd]")
        output.muted(f"config: {config.path}")
        return 0

    # Render in declared group order, default first.
    seen_groups: set[str] = set()
    ordered: list[str] = []
    if any(a.group == DEFAULT_GROUP for a in config.aliases):
        ordered.append(DEFAULT_GROUP)
        seen_groups.add(DEFAULT_GROUP)
    for g in config.groups:
        if g in seen_groups:
            continue
        if any(a.group == g for a in config.aliases):
            ordered.append(g)
            seen_groups.add(g)
    # Catch any alias whose group wasn't declared in the file (shouldn't happen).
    for a in config.aliases:
        if a.group not in seen_groups:
            ordered.append(a.group)
            seen_groups.add(a.group)

    first = True
    for g in ordered:
        members = [a for a in config.aliases if a.group == g]
        if not members:
            continue
        if not first:
            output.info("")
        first = False
        _render_group(config, g, members)
    return 0

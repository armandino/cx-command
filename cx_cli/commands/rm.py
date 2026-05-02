"""`cx rm <name>` — remove alias, warning about letter shifts."""
from __future__ import annotations

from .. import config as cfg
from .. import output


def run(config: cfg.Config, name: str) -> int:
    alias = config.by_name(name)
    if alias is None:
        output.error(f"no such alias: '{name}'")
        return 1
    idx = config.aliases.index(alias)
    triples = [
        (a.name, a.raw_path, a.group)
        for a in config.aliases if a.name != name
    ]
    cfg.save(config, triples)
    output.success(f"removed alias '{name}' ({alias.letter}) \\[{alias.group}]")
    shifted = config.aliases[idx + 1:]
    if shifted:
        names = ", ".join(a.name for a in shifted)
        output.note(f"letters shifted for later aliases: {names}")
    return 0

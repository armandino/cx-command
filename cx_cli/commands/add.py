"""`cx add <name> <path> [-g <group>]` — add alias with validation."""
from __future__ import annotations

import os

from rich.markup import escape

from .. import config as cfg
from .. import output


def run(config: cfg.Config, name: str, raw_path: str,
        group: str = cfg.DEFAULT_GROUP) -> int:
    existing = set(config.names)
    try:
        cfg.validate_name(name, existing)
        cfg.validate_group(group)
    except cfg.ValidationError as e:
        output.error(str(e))
        return 1

    stored: str
    warn: str | None = None
    try:
        import re
        has_var = bool(re.search(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*", raw_path))
        if has_var:
            stored = raw_path
            warn = (f"stored with unexpanded env vars — directory existence"
                    f" will be checked at use time")
        else:
            expanded = os.path.expanduser(raw_path)
            abs_path = os.path.abspath(expanded)
            if not os.path.exists(abs_path):
                raise cfg.ValidationError(f"path does not exist: {abs_path}")
            if not os.path.isdir(abs_path):
                raise cfg.ValidationError(f"path is not a directory: {abs_path}")
            stored = abs_path
    except cfg.ValidationError as e:
        output.error(str(e))
        return 1

    triples = [(a.name, a.raw_path, a.group) for a in config.aliases]
    triples.append((name, stored, group))
    cfg.save(config, triples)
    letter = cfg._letter_for_index(len(triples) - 1)
    output.success(
        f"added alias '{name}' ({letter}) \\[{group}] -> {escape(stored)}"
    )
    if warn:
        output.note(warn)
    return 0

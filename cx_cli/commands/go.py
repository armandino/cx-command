"""Default subcommand: cd to alias/letter/subpath, or `cx -` for previous."""
from __future__ import annotations

import os

from .. import history, output, resolver
from ..config import Config


def run(config: Config, target: str) -> int:
    if target == "-":
        prev = history.previous()
        if not prev:
            output.error("no previous directory in history")
            return 1
        history.append(prev, config.settings.history_size)
        output.cd(prev)
        return 0
    try:
        r = resolver.resolve(config, target)
    except resolver.ResolveError as e:
        output.error(str(e))
        return 1
    if not os.path.isdir(r.path):
        output.error(f"not a directory: {r.path}")
        return 1
    history.append(r.path, config.settings.history_size)
    output.cd(r.path)
    return 0

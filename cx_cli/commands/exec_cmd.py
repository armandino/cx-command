"""`cx exec <name>[/sub] -- cmd args` — run arbitrary command in resolved dir."""
from __future__ import annotations

import os

from .. import output, resolver
from ..config import Config


def run(config: Config, target: str, argv: list[str]) -> int:
    if not argv:
        output.error("exec: command required after '--'")
        return 1
    try:
        r = resolver.resolve(config, target)
    except resolver.ResolveError as e:
        output.error(str(e))
        return 1
    if not os.path.isdir(r.path):
        output.error(f"not a directory: {r.path}")
        return 1
    output.exec_in(r.path, argv)
    return 0

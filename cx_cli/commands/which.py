"""`cx which <name>[/sub]` — print resolved path only (scriptable)."""
from __future__ import annotations

import sys

from .. import output, resolver
from ..config import Config


def run(config: Config, target: str) -> int:
    try:
        r = resolver.resolve(config, target)
    except resolver.ResolveError as e:
        output.error(str(e))
        return 1
    # Plain stdout — no directive — so $(cx which ...) is usable.
    sys.stdout.write(r.path + "\n")
    return 0

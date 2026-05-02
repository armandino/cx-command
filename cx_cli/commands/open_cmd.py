"""`cx open [<name>[/sub[/file]]] [-w <opener>]` — open with configured opener.

Opener resolution order:
  1. --with/-w <name>  → look up in [openers] (falls back to literal command)
  2. settings.opener   → look up in [openers] (falls back to literal command)
  3. platform default  (explorer / open / xdg-open)

The opener command string is shlex-split. If it contains `{path}`, the target
path is substituted into each occurrence; otherwise the path is appended as the
final argument. Targets can be files OR directories.
"""
from __future__ import annotations

import os
import shlex

from .. import output, platform as plat, resolver
from ..config import Config


def _resolve_opener_cmd(config: Config, name: str | None) -> str:
    """Return the command string for the given opener name (or the default)."""
    openers = config.settings.openers or {}
    if name is not None:
        # Explicit --with: keyed value first, else treat name as literal command.
        return openers.get(name, name)
    # No --with: use settings.opener (keyed lookup, else literal), else platform.
    default = config.settings.opener
    if default is None:
        return plat.default_opener()
    return openers.get(default, default)


def run(config: Config, target: str | None, opener_name: str | None = None) -> int:
    if target is None:
        path = os.getcwd()
    else:
        try:
            r = resolver.resolve(config, target)
        except resolver.ResolveError as e:
            output.error(str(e))
            return 1
        if not os.path.exists(r.path):
            output.error(f"path does not exist: {r.path}")
            return 1
        path = r.path

    # On Cygwin, translate to Windows form — most Windows openers (explorer,
    # cygstart-launched apps) want Windows paths, and VSCode handles both.
    if plat.is_cygwin():
        path = plat.cygpath_w(path)

    cmd_str = _resolve_opener_cmd(config, opener_name)
    try:
        tokens = shlex.split(cmd_str, posix=True)
    except ValueError as e:
        output.error(f"invalid opener command {cmd_str!r}: {e}")
        return 1
    if not tokens:
        output.error(f"empty opener for {opener_name or 'default'!r}")
        return 1

    # {path} substitution, else append.
    if any("{path}" in t for t in tokens):
        tokens = [t.replace("{path}", path) for t in tokens]
    else:
        tokens.append(path)

    output.open_dir(tokens)
    return 0

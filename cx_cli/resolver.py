"""Alias + sub-path + env-var + cygpath resolution."""
from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass

from . import platform as plat
from .config import Config, Alias


class ResolveError(ValueError):
    pass


@dataclass
class Resolved:
    alias: Alias
    subpath: str  # "" if none
    path: str    # final resolved path (absolute, POSIX on Cygwin)


_VAR_RE = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def expand_env(raw: str, env: dict[str, str] | None = None) -> str:
    """Expand ${VAR} and $VAR. Raise ResolveError for unresolved vars."""
    e = env if env is not None else os.environ

    def sub(m: re.Match) -> str:
        name = m.group(1) or m.group(2)
        if name not in e:
            raise ResolveError(f"unresolved env var: ${{{name}}}")
        return e[name]

    return _VAR_RE.sub(sub, raw)


def split_target(target: str) -> tuple[str, str]:
    """Split an alias spec like 'foo/src/main' into ('foo', 'src/main')."""
    if "/" in target:
        head, _, tail = target.partition("/")
        return head, tail
    return target, ""


def lookup(config: Config, head: str) -> Alias:
    """Find alias by name or letter. Raise ResolveError with suggestion on miss."""
    a = config.by_name(head)
    if a:
        return a
    a = config.by_letter(head)
    if a:
        return a
    suggestions = difflib.get_close_matches(head, config.names, n=1, cutoff=0.6)
    hint = f" Did you mean '{suggestions[0]}'?" if suggestions else ""
    raise ResolveError(f"unknown alias '{head}'.{hint}")


def resolve(config: Config, target: str,
            env: dict[str, str] | None = None) -> Resolved:
    head, sub = split_target(target)
    alias = lookup(config, head)
    expanded = expand_env(alias.raw_path, env)
    expanded = os.path.expanduser(expanded)
    if sub:
        expanded = os.path.join(expanded, sub)
    # Translate Windows-style paths on Cygwin
    path = plat.cygpath_u(expanded)
    # Normalize (collapse .., //)
    path = os.path.normpath(path)
    return Resolved(alias=alias, subpath=sub, path=path)

"""`cx __complete <cword> <words...>` — bash completion helper.

Prints candidates one per line (newlines preserved). The caller in cx.sh
feeds them into `compgen -W`.
"""
from __future__ import annotations

import os
import sys

from . import config as cfg_mod
from . import resolver

SUBCOMMANDS = [
    "add", "rm", "edit", "help", "init", "recent", "open", "ls", "exec", "which",
]


def _print(items):
    for it in items:
        print(it)


def _alias_tokens(config) -> list[str]:
    # Letters (a, b, c, ...) are intentionally excluded from tab completion —
    # they're short by design and cluttering completion with them defeats
    # their purpose.
    return [a.name for a in config.aliases]


def _subpath_candidates(config, target: str, include_files: bool = False) -> list[str]:
    """Path completion inside an alias sub-path.

    target: e.g. 'foo/', 'foo/src', 'b/src/ma'
    include_files: when True, include regular files (e.g. for `cx open`).
    """
    head, sub = resolver.split_target(target)
    alias = config.by_name(head) or config.by_letter(head)
    if alias is None:
        return []
    try:
        r = resolver.resolve(config, head)
    except resolver.ResolveError:
        return []
    base_dir = r.path
    rel_dir, _, partial = sub.rpartition("/")
    scan_dir = os.path.join(base_dir, rel_dir) if rel_dir else base_dir
    if not os.path.isdir(scan_dir):
        return []
    results: list[str] = []
    prefix = f"{head}/" + (f"{rel_dir}/" if rel_dir else "")
    try:
        entries = os.listdir(scan_dir)
    except OSError:
        return []
    for e in sorted(entries):
        if partial and not e.startswith(partial):
            continue
        full = os.path.join(scan_dir, e)
        if os.path.isdir(full):
            results.append(f"{prefix}{e}/")
        elif include_files and os.path.isfile(full):
            results.append(f"{prefix}{e}")
    return results


def handle(argv: list[str]) -> int:
    """argv = sys.argv[2:] — [cword, words...]"""
    if not argv:
        return 0
    try:
        cword = int(argv[0])
    except ValueError:
        return 0
    words = argv[1:]  # words[0] is 'cx'
    cur = words[cword] if cword < len(words) else ""

    try:
        config = cfg_mod.load()
    except Exception:
        return 0

    if cword == 1:
        # first positional: subcommands + alias names + letters, or sub-path
        if "/" in cur:
            _print(_subpath_candidates(config, cur))
        else:
            _print(SUBCOMMANDS)
            _print(_alias_tokens(config))
        return 0

    cmd = words[1] if len(words) > 1 else ""

    if cmd == "rm":
        if cword == 2:
            _print([a.name for a in config.aliases])
        return 0
    if cmd in ("which", "ls", "exec"):
        if cword == 2:
            if "/" in cur:
                _print(_subpath_candidates(config, cur))
            else:
                _print(_alias_tokens(config))
        return 0
    if cmd == "open":
        # cx open [<target>] [-w/--with <opener>]
        prev = words[cword - 1] if cword - 1 < len(words) else ""
        if prev in ("-w", "--with"):
            openers = config.settings.openers or {}
            _print(sorted(openers.keys()))
            return 0
        if cur.startswith("-"):
            _print(["-w", "--with"])
            return 0
        if "/" in cur:
            _print(_subpath_candidates(config, cur, include_files=True))
        else:
            _print(_alias_tokens(config))
        return 0
    if cmd == "init":
        if cword == 2:
            _print(["bash"])
        return 0
    if cmd == "add":
        # cx add <name> <path> [-g/--group <group>]
        # Heuristic completion: -g/--group anywhere; values from existing groups.
        prev = words[cword - 1] if cword - 1 < len(words) else ""
        if prev in ("-g", "--group"):
            _print(sorted(set(a.group for a in config.aliases)))
            return 0
        if cur.startswith("-"):
            _print(["-g", "--group"])
            return 0
        # cword == 2: name (freeform); cword == 3: path (handled by shell).
        return 0
    if cmd == "help":
        if cword == 2:
            _print(SUBCOMMANDS)
        return 0
    if cmd == "recent":
        return 0

    # Default: alias/letter, with sub-path expansion after '/'
    if cword == 1 or (cword == 2 and cmd not in SUBCOMMANDS):
        pass  # already handled above

    if "/" in cur:
        _print(_subpath_candidates(config, cur))
    else:
        _print(_alias_tokens(config))
    return 0

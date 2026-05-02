"""cx CLI dispatch."""
from __future__ import annotations

import sys

from . import completion, config as cfg_mod, output
from .commands import (
    add, edit, exec_cmd, go, help_cmd, init, list_cmd, ls, open_cmd, recent, rm, which,
)

SUBCOMMANDS = {
    "add", "rm", "edit", "help", "init", "recent", "open", "ls", "exec", "which",
}


def _split_extra(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv on the first '--'. Returns (before, after); after is [] if no '--'."""
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1:]
    return argv, []


def _dispatch(argv: list[str]) -> int:
    # Fast-path: hidden completion hook
    if argv and argv[0] == "__complete":
        return completion.handle(argv[1:])

    # No args → list
    if not argv:
        try:
            config = cfg_mod.load()
        except Exception as e:
            output.error(f"config error: {e}")
            return 1
        return list_cmd.run(config)

    first = argv[0]

    # Help (before loading config so --help always works)
    if first in ("help", "-h", "--help"):
        return help_cmd.run()

    # Previous dir shortcut
    if first == "-":
        try:
            config = cfg_mod.load()
        except Exception as e:
            output.error(f"config error: {e}")
            return 1
        return go.run(config, "-")

    try:
        config = cfg_mod.load()
    except Exception as e:
        output.error(f"config error: {e}")
        return 1

    if first not in SUBCOMMANDS:
        # Treat as alias/letter[/sub]
        if len(argv) > 1:
            output.error(f"unexpected extra args: {argv[1:]}")
            return 2
        return go.run(config, first)

    rest = argv[1:]

    if first == "init":
        if len(rest) != 1:
            output.error("usage: cx init <shell>")
            return 2
        return init.run(rest[0])
    if first == "add":
        # cx add <name> <path> [-g/--group <group>]
        group = None
        positional: list[str] = []
        i = 0
        while i < len(rest):
            arg = rest[i]
            if arg in ("-g", "--group"):
                if i + 1 >= len(rest):
                    output.error("usage: cx add <name> <path> [-g <group>]")
                    return 2
                group = rest[i + 1]
                i += 2
                continue
            if arg.startswith("--group="):
                group = arg.split("=", 1)[1]
                i += 1
                continue
            positional.append(arg)
            i += 1
        if len(positional) != 2:
            output.error("usage: cx add <name> <path> [-g <group>]")
            return 2
        from .config import DEFAULT_GROUP
        return add.run(config, positional[0], positional[1],
                       group or DEFAULT_GROUP)
    if first == "rm":
        if len(rest) != 1:
            output.error("usage: cx rm <name>")
            return 2
        return rm.run(config, rest[0])
    if first == "edit":
        if rest:
            output.error("usage: cx edit")
            return 2
        return edit.run(config)
    if first == "recent":
        if len(rest) > 1:
            output.error("usage: cx recent [N]")
            return 2
        return recent.run(config, rest[0] if rest else None)
    if first == "open":
        # cx open [<target>] [-w/--with <opener>]
        opener_name: str | None = None
        positional: list[str] = []
        i = 0
        while i < len(rest):
            arg = rest[i]
            if arg in ("-w", "--with"):
                if i + 1 >= len(rest):
                    output.error("usage: cx open [<name>[/sub]] [-w <opener>]")
                    return 2
                opener_name = rest[i + 1]
                i += 2
                continue
            if arg.startswith("--with="):
                opener_name = arg.split("=", 1)[1]
                i += 1
                continue
            positional.append(arg)
            i += 1
        if len(positional) > 1:
            output.error("usage: cx open [<name>[/sub]] [-w <opener>]")
            return 2
        return open_cmd.run(
            config,
            positional[0] if positional else None,
            opener_name,
        )
    if first == "which":
        if len(rest) != 1:
            output.error("usage: cx which <name>[/sub]")
            return 2
        return which.run(config, rest[0])
    if first == "ls":
        before, after = _split_extra(rest)
        if len(before) != 1:
            output.error("usage: cx ls <name>[/sub] [-- ls-args]")
            return 2
        return ls.run(config, before[0], after)
    if first == "exec":
        before, after = _split_extra(rest)
        if len(before) != 1 or not after:
            output.error("usage: cx exec <name>[/sub] -- cmd [args...]")
            return 2
        return exec_cmd.run(config, before[0], after)

    output.error(f"unknown subcommand: {first}")
    return 2


def main() -> None:
    try:
        rc = _dispatch(sys.argv[1:])
    except KeyboardInterrupt:
        output.error("interrupted")
        rc = 130
    except Exception as e:  # last-resort safety net
        output.error(f"internal error: {e}")
        rc = 1
    sys.exit(rc)

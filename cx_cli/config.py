"""Config load/save, alias model, letter assignment, validation.

Aliases are organized into named groups for display/organization purposes only.
The default group is "default" and corresponds to the bare `[aliases]` TOML
table. Additional groups are defined as sub-tables, e.g. `[aliases.projects]`.

- Names must be globally unique across all groups.
- Letters (a, b, c, …) are assigned globally in file insertion order.
- Group order in the file determines display order; the default group appears
  first if it has any keys.
"""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CONFIG_PATH = Path.home() / ".cxrc.toml"
DEFAULT_GROUP = "default"

RESERVED_SUBCOMMANDS = frozenset({
    "add", "rm", "edit", "help", "init", "recent", "open", "ls", "exec", "which",
    "-", "__complete",
})
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
GROUP_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
SINGLE_LETTER = re.compile(r"^[A-Za-z]$")

DEFAULT_CONFIG = """\
# cx — directory navigation config
# Letters are auto-assigned in the order aliases appear below (a, b, c, ... aa, ab, ...).
# Paths support ${VAR} / $VAR env-var expansion and ~ home expansion.
#
# Aliases are organized into groups for display only. `[aliases]` is the default
# group; `[aliases.<group>]` defines a named group. Names are globally unique.

[settings]
# opener = "xdg-open"     # e.g. Cygwin: explorer; Linux default: xdg-open
history_size = 50

[aliases]
# downloads  = "~/Downloads"

[aliases.projects]
# projects = "~/projects"
# foo = "~/projects/foo"
"""


@dataclass(frozen=True)
class Alias:
    name: str
    raw_path: str    # as-stored in config (may contain ${VAR}, ~, relative)
    letter: str      # assigned on load (a, b, ..., z, aa, ab, ...)
    group: str       # group name (DEFAULT_GROUP for ungrouped)


@dataclass
class Settings:
    opener: str | None = None
    history_size: int = 50
    openers: dict[str, str] | None = None  # name -> command string


@dataclass
class Config:
    settings: Settings
    aliases: list[Alias]   # in insertion order (across all groups)
    groups: list[str]      # group names in declaration order
    path: Path

    def by_name(self, name: str) -> Alias | None:
        for a in self.aliases:
            if a.name == name:
                return a
        return None

    def by_letter(self, letter: str) -> Alias | None:
        for a in self.aliases:
            if a.letter == letter:
                return a
        return None

    @property
    def names(self) -> list[str]:
        return [a.name for a in self.aliases]

    def aliases_in_group(self, group: str) -> list[Alias]:
        return [a for a in self.aliases if a.group == group]


def _letter_for_index(i: int) -> str:
    """Return a, b, ..., z, aa, ab, ..., zz, aaa, ... for non-negative i."""
    if i < 0:
        raise ValueError(i)
    letters = ""
    n = i
    while True:
        letters = chr(ord("a") + (n % 26)) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


_KV_DOUBLE = re.compile(r'^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*"(.*)"\s*(?:#.*)?$')
_KV_SINGLE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*'(.*)'\s*(?:#.*)?$")
_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")


def _parse_ordered_aliases(raw: bytes) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Parse `[aliases]` and `[aliases.<group>]` blocks preserving insertion order.

    Returns:
        triples: list of (name, raw_path, group) in file order
        groups:  list of group names in the order they were declared

    Duplicate names (across any group) are silently dropped after the first
    occurrence — validation happens at write time.
    """
    text = raw.decode("utf-8")
    lines = text.splitlines()
    triples: list[tuple[str, str, str]] = []
    groups: list[str] = []
    seen_names: set[str] = set()
    seen_groups: set[str] = set()
    current_group: str | None = None  # None = not in an aliases section

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m_section = _SECTION.match(line)
        if m_section:
            section = m_section.group(1).strip()
            if section == "aliases":
                current_group = DEFAULT_GROUP
            elif section.startswith("aliases."):
                g = section[len("aliases."):].strip()
                current_group = g if GROUP_REGEX.match(g) else None
            else:
                current_group = None
            if current_group is not None and current_group not in seen_groups:
                seen_groups.add(current_group)
                groups.append(current_group)
            continue
        if current_group is None:
            continue
        m = _KV_DOUBLE.match(line) or _KV_SINGLE.match(line)
        if m:
            name, val = m.group(1), m.group(2)
            if name in seen_names:
                continue
            seen_names.add(name)
            triples.append((name, val, current_group))
    return triples, groups


def load(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    s = data.get("settings", {}) or {}
    openers_raw = data.get("openers", {}) or {}
    # Coerce to str->str; ignore non-string values silently.
    openers = {k: str(v) for k, v in openers_raw.items() if isinstance(v, str)}
    settings = Settings(
        opener=s.get("opener"),
        history_size=int(s.get("history_size", 50)),
        openers=openers,
    )
    triples, groups = _parse_ordered_aliases(raw)
    aliases = [
        Alias(name=n, raw_path=p, letter=_letter_for_index(i), group=g)
        for i, (n, p, g) in enumerate(triples)
    ]
    # Ensure default group is present when there are any aliases at all,
    # so callers can always reference it.
    if DEFAULT_GROUP not in groups:
        groups.insert(0, DEFAULT_GROUP)
    return Config(settings=settings, aliases=aliases, groups=groups, path=path)


# ---------- writer ----------

def _quote(val: str) -> str:
    """TOML basic-string quote: escape " and \\."""
    escaped = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render(
    settings: Settings,
    triples: Iterable[tuple[str, str, str]],
    group_order: list[str],
) -> str:
    triples_list = list(triples)
    # Bucket by group, preserving per-group insertion order.
    by_group: dict[str, list[tuple[str, str]]] = {}
    encounter_order: list[str] = []
    for name, path, group in triples_list:
        if group not in by_group:
            by_group[group] = []
            encounter_order.append(group)
        by_group[group].append((name, path))

    # Final ordering: declared group_order first (filtered to non-empty groups),
    # then any new groups in encounter order. Default group is always first if
    # it has any keys — even when not first in declared order — to keep the
    # ungrouped section visually on top.
    ordered: list[str] = []
    seen: set[str] = set()
    if DEFAULT_GROUP in by_group:
        ordered.append(DEFAULT_GROUP)
        seen.add(DEFAULT_GROUP)
    for g in list(group_order) + encounter_order:
        if g in by_group and g not in seen:
            ordered.append(g)
            seen.add(g)

    out: list[str] = []
    out.append("# cx — directory navigation config")
    out.append("# Letters are auto-assigned in the order aliases appear below"
               " (a, b, c, ... aa, ab, ...).")
    out.append("# Paths support ${VAR} / $VAR env-var expansion and ~ home"
               " expansion.")
    out.append("#")
    out.append("# Aliases are organized into groups for display only."
               " `[aliases]` is the default")
    out.append("# group; `[aliases.<group>]` defines a named group."
               " Names are globally unique.")
    out.append("")
    out.append("[settings]")
    if settings.opener is not None:
        out.append(f"opener = {_quote(settings.opener)}")
    out.append(f"history_size = {int(settings.history_size)}")
    out.append("")

    if settings.openers:
        out.append("[openers]")
        for name, cmd in settings.openers.items():
            out.append(f"{name} = {_quote(cmd)}")
        out.append("")

    # Always emit at least an empty [aliases] section for discoverability.
    if not ordered:
        out.append("[aliases]")
        out.append("")
        return "\n".join(out)

    for g in ordered:
        header = "[aliases]" if g == DEFAULT_GROUP else f"[aliases.{g}]"
        out.append(header)
        for name, raw_path in by_group[g]:
            out.append(f"{name} = {_quote(raw_path)}")
        out.append("")
    return "\n".join(out)


def save(
    config: Config,
    triples: list[tuple[str, str, str]] | None = None,
) -> None:
    """Save config; if `triples` is None uses current aliases."""
    if triples is None:
        triples = [(a.name, a.raw_path, a.group) for a in config.aliases]
    text = _render(config.settings, triples, config.groups)
    config.path.write_text(text, encoding="utf-8")


# ---------- validation ----------

class ValidationError(ValueError):
    pass


def validate_name(name: str, existing: set[str]) -> None:
    if not name:
        raise ValidationError("alias name is required")
    if len(name) < 2:
        raise ValidationError(
            f"alias name must be at least 2 characters: '{name}'"
        )
    if SINGLE_LETTER.match(name):
        raise ValidationError(
            f"alias name '{name}' is reserved (single letters a-z are"
            " auto-assigned letter shortcuts)"
        )
    if not NAME_REGEX.match(name):
        raise ValidationError(
            f"invalid alias name '{name}': must match [A-Za-z][A-Za-z0-9_-]*"
        )
    if name.startswith("__"):
        raise ValidationError(
            f"alias name '{name}' is reserved (leading __ is reserved)"
        )
    if name in RESERVED_SUBCOMMANDS:
        raise ValidationError(
            f"alias name '{name}' collides with a reserved subcommand"
        )
    if name in existing:
        raise ValidationError(
            f"alias '{name}' already exists (use 'cx rm {name}' first)"
        )


def validate_group(group: str) -> None:
    if not group:
        raise ValidationError("group name is required")
    if not GROUP_REGEX.match(group):
        raise ValidationError(
            f"invalid group name '{group}': must match [A-Za-z][A-Za-z0-9_-]*"
        )


def validate_path(raw_path: str) -> tuple[str, bool]:
    """Return (stored_path, had_unexpanded_vars).

    - If path contains ${VAR} / $VAR, store verbatim; caller may warn.
    - Otherwise expand ~, make absolute, and require it to be an existing dir.
    """
    if not raw_path:
        raise ValidationError("path is required")
    has_var = bool(re.search(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*", raw_path))
    if has_var:
        return raw_path, True
    expanded = os.path.expanduser(raw_path)
    abs_path = os.path.abspath(expanded)
    if not os.path.exists(abs_path):
        raise ValidationError(f"path does not exist: {abs_path}")
    if not os.path.isdir(abs_path):
        raise ValidationError(f"path is not a directory: {abs_path}")
    return abs_path, False

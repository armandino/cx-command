from pathlib import Path

import pytest

from cx_cli import config as cfg
from cx_cli import resolver


def _mk_config(tmp_path: Path, pairs):
    p = tmp_path / "cxrc.toml"
    lines = ["[settings]\n", "[aliases]\n"]
    for n, v in pairs:
        lines.append(f'{n} = "{v}"\n')
    p.write_text("".join(lines), encoding="utf-8")
    return cfg.load(p)


def test_split_target():
    assert resolver.split_target("foo") == ("foo", "")
    assert resolver.split_target("foo/") == ("foo", "")
    assert resolver.split_target("foo/bar/baz") == ("foo", "bar/baz")


def test_expand_env_basic():
    env = {"X": "hello", "Y": "world"}
    assert resolver.expand_env("${X}/$Y/path", env) == "hello/world/path"


def test_expand_env_missing():
    with pytest.raises(resolver.ResolveError):
        resolver.expand_env("${NOPE}/x", {})


def test_lookup_by_name(tmp_path: Path):
    c = _mk_config(tmp_path, [("foo", str(tmp_path)), ("bar", str(tmp_path))])
    a = resolver.lookup(c, "foo")
    assert a.name == "foo"


def test_lookup_by_letter(tmp_path: Path):
    c = _mk_config(tmp_path, [("foo", str(tmp_path)), ("bar", str(tmp_path))])
    a = resolver.lookup(c, "b")
    assert a.name == "bar"


def test_lookup_unknown_suggests(tmp_path: Path):
    c = _mk_config(tmp_path, [("source", str(tmp_path))])
    with pytest.raises(resolver.ResolveError) as ei:
        resolver.lookup(c, "sourxe")
    assert "source" in str(ei.value)


def test_resolve_subpath(tmp_path: Path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    c = _mk_config(tmp_path, [("root", str(tmp_path))])
    r = resolver.resolve(c, "root/a/b")
    assert Path(r.path) == sub
    assert r.subpath == "a/b"


def test_resolve_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CX_TEST_ROOT", str(tmp_path))
    c = _mk_config(tmp_path, [("x", "${CX_TEST_ROOT}")])
    r = resolver.resolve(c, "x")
    assert Path(r.path) == tmp_path

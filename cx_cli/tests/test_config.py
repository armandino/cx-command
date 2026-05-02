from pathlib import Path

import pytest

from cx_cli import config as cfg


def test_letter_for_index_basic():
    assert cfg._letter_for_index(0) == "a"
    assert cfg._letter_for_index(25) == "z"
    assert cfg._letter_for_index(26) == "aa"
    assert cfg._letter_for_index(27) == "ab"
    assert cfg._letter_for_index(26 + 25) == "az"
    assert cfg._letter_for_index(26 + 26) == "ba"
    assert cfg._letter_for_index(26 * 27 - 1) == "zz"
    assert cfg._letter_for_index(26 * 27) == "aaa"


def test_load_missing_creates_default(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    c = cfg.load(p)
    assert p.exists()
    # Default template seeds a 'user' group example.
    assert [a.name for a in c.aliases] == ["user-settings"]
    assert c.aliases[0].group == "user"
    assert c.settings.history_size == 50


def test_load_parses_aliases_in_order(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text(
        '[settings]\nhistory_size = 10\n'
        '[aliases]\n'
        'src = "/tmp"\n'
        'foo = "${SRC}/main"\n'
        'nb = "~/notebook"\n',
        encoding="utf-8",
    )
    c = cfg.load(p)
    assert [a.name for a in c.aliases] == ["src", "foo", "nb"]
    assert [a.letter for a in c.aliases] == ["a", "b", "c"]
    assert all(a.group == cfg.DEFAULT_GROUP for a in c.aliases)
    assert c.aliases[1].raw_path == "${SRC}/main"
    assert c.settings.history_size == 10


def test_save_round_trip(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text('[settings]\n[aliases]\n', encoding="utf-8")
    c = cfg.load(p)
    triples = [
        ("foo", "/tmp", cfg.DEFAULT_GROUP),
        ("bar", "${X}/y", cfg.DEFAULT_GROUP),
    ]
    cfg.save(c, triples)
    c2 = cfg.load(p)
    assert [(a.name, a.raw_path, a.group) for a in c2.aliases] == triples
    assert [a.letter for a in c2.aliases] == ["a", "b"]


def test_save_preserves_settings(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text('[settings]\nhistory_size = 7\nopener = "code"\n'
                 '[aliases]\nfoo = "/tmp"\n', encoding="utf-8")
    c = cfg.load(p)
    cfg.save(c)
    c2 = cfg.load(p)
    assert c2.settings.history_size == 7
    assert c2.settings.opener == "code"
    assert [a.name for a in c2.aliases] == ["foo"]


def test_load_parses_groups(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text(
        '[settings]\n'
        '[aliases]\n'
        'nb = "/tmp"\n'
        '[aliases.bars]\n'
        'baxx = "/tmp/baxx"\n'
        '[aliases.projects]\n'
        'foo = "/tmp/foo"\n'
        'mm = "/tmp/mm"\n',
        encoding="utf-8",
    )
    c = cfg.load(p)
    assert [a.name for a in c.aliases] == ["nb", "baxx", "foo", "mm"]
    assert [a.group for a in c.aliases] == [
        cfg.DEFAULT_GROUP, "bars", "projects", "projects",
    ]
    # Letters assigned globally in file order.
    assert [a.letter for a in c.aliases] == ["a", "b", "c", "d"]
    assert c.groups[0] == cfg.DEFAULT_GROUP
    assert "bars" in c.groups and "projects" in c.groups


def test_save_emits_group_subtables(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text('[settings]\n[aliases]\n', encoding="utf-8")
    c = cfg.load(p)
    triples = [
        ("nb", "/tmp", cfg.DEFAULT_GROUP),
        ("baxx", "/tmp/d", "bars"),
        ("foo", "/tmp/b", "projects"),
    ]
    cfg.save(c, triples)
    text = p.read_text(encoding="utf-8")
    assert "[aliases]" in text
    assert "[aliases.bars]" in text
    assert "[aliases.projects]" in text
    # Default group keys appear in [aliases] block (before sub-tables).
    assert text.index("[aliases]\n") < text.index("[aliases.bars]")
    c2 = cfg.load(p)
    assert [(a.name, a.group) for a in c2.aliases] == [
        ("nb", cfg.DEFAULT_GROUP), ("baxx", "bars"), ("foo", "projects"),
    ]


def test_save_default_group_first_even_when_added_last(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text('[settings]\n[aliases.bars]\nbaxx = "/tmp/d"\n', encoding="utf-8")
    c = cfg.load(p)
    triples = [
        ("baxx", "/tmp/d", "bars"),
        ("nb", "/tmp", cfg.DEFAULT_GROUP),  # added later but should render first
    ]
    cfg.save(c, triples)
    text = p.read_text(encoding="utf-8")
    assert text.index("[aliases]\n") < text.index("[aliases.bars]")


def test_openers_parsed(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text(
        '[settings]\nopener = "explorer"\n'
        '[openers]\nexplorer = "explorer"\n'
        'code = "code --new-window"\n'
        '[aliases]\n',
        encoding="utf-8",
    )
    c = cfg.load(p)
    assert c.settings.openers == {
        "explorer": "explorer",
        "code": "code --new-window",
    }


def test_openers_round_trip(tmp_path: Path):
    p = tmp_path / "cxrc.toml"
    p.write_text('[settings]\n[aliases]\n', encoding="utf-8")
    c = cfg.load(p)
    c.settings.openers = {"code": "code", "diff": "meld"}
    cfg.save(c)
    text = p.read_text(encoding="utf-8")
    assert "[openers]" in text
    c2 = cfg.load(p)
    assert c2.settings.openers == {"code": "code", "diff": "meld"}


@pytest.mark.parametrize("bad", ["a", "z", "1foo", "-foo", "", "__hidden"])
def test_validate_name_rejects_bad(bad):
    with pytest.raises(cfg.ValidationError):
        cfg.validate_name(bad, set())


@pytest.mark.parametrize("reserved", ["add", "rm", "edit", "open", "ls", "exec",
                                       "which", "recent", "help"])
def test_validate_name_rejects_reserved(reserved):
    with pytest.raises(cfg.ValidationError):
        cfg.validate_name(reserved, set())


def test_validate_name_rejects_collision():
    with pytest.raises(cfg.ValidationError):
        cfg.validate_name("foo", {"foo"})


def test_validate_name_accepts_valid():
    cfg.validate_name("foo", set())
    cfg.validate_name("my-dir_2", set())


def test_validate_path_env_var_skips_check():
    stored, had_var = cfg.validate_path("${NOWHERE}/x")
    assert had_var is True
    assert stored == "${NOWHERE}/x"


def test_validate_path_existing_dir(tmp_path: Path):
    stored, had_var = cfg.validate_path(str(tmp_path))
    assert had_var is False
    assert Path(stored).is_absolute()


def test_validate_path_missing(tmp_path: Path):
    with pytest.raises(cfg.ValidationError):
        cfg.validate_path(str(tmp_path / "nope"))


def test_validate_path_not_dir(tmp_path: Path):
    f = tmp_path / "file"
    f.write_text("x")
    with pytest.raises(cfg.ValidationError):
        cfg.validate_path(str(f))

from cx_cli.config import _letter_for_index


def test_first_26():
    expected = [chr(ord("a") + i) for i in range(26)]
    actual = [_letter_for_index(i) for i in range(26)]
    assert actual == expected


def test_second_26():
    assert _letter_for_index(26) == "aa"
    assert _letter_for_index(26 + 25) == "az"


def test_third_26():
    assert _letter_for_index(52) == "ba"
    assert _letter_for_index(52 + 25) == "bz"


def test_boundary_to_three_letters():
    assert _letter_for_index(26 * 27 - 1) == "zz"
    assert _letter_for_index(26 * 27) == "aaa"

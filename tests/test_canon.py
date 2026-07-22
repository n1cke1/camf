import math

import pytest

from camf import canon


def test_nfc_applied_to_strings():
    composed, decomposed = "é", "é"
    assert composed != decomposed
    assert canon.encode_row([decomposed], ["str"]) == canon.encode_row([composed], ["str"])


def test_negative_zero_folded():
    assert canon.canon_float(-0.0) == 0.0
    assert math.copysign(1.0, canon.canon_float(-0.0)) == 1.0
    assert canon.encode_row([-0.0], ["f64"]) == canon.encode_row([0.0], ["f64"])
    assert canon.js_number(-0.0) == "0"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_rejected(value):
    with pytest.raises(ValueError):
        canon.canon_float(value)


@pytest.mark.parametrize("value,expected", [
    (0.0, "0"), (1.0, "1"), (100.0, "100"), (1.5, "1.5"), (0.1, "0.1"),
    (-1.5, "-1.5"),
    # ECMAScript switches to exponential outside (1e-6, 1e21); Python's repr
    # switches elsewhere, which is exactly what js_number has to repair.
    (1e-5, "0.00001"), (1e-6, "0.000001"), (1e-7, "1e-7"),
    (1e17, "100000000000000000"), (1e21, "1e+21"), (5e-324, "5e-324"),
])
def test_js_number(value, expected):
    assert canon.js_number(value) == expected


def test_jcs_sorts_by_utf16_code_units():
    # Non-BMP characters sort before U+FB00 in UTF-16 but after it in code
    # points, so a code-point sort would produce different bytes here.
    out = canon.jcs({"ﬀ": 1, "\U0001f600": 2, "é": 3}).decode("utf-8")
    assert out.index("é") < out.index("\U0001f600") < out.index("ﬀ")


def test_jcs_has_no_insignificant_whitespace():
    assert canon.jcs({"b": [1, 2], "a": {"y": True, "x": None}}) == \
        b'{"a":{"x":null,"y":true},"b":[1,2]}'


def test_jcs_escapes_minimally():
    assert canon.jcs({"k": 'a"b\\c\nd\x01'}) == b'{"k":"a\\"b\\\\c\\nd\\u0001"}'


def test_jcs_rejects_inexact_integers():
    with pytest.raises(ValueError):
        canon.jcs({"n": 2 ** 53 + 1})


def test_row_encoding_is_type_and_order_sensitive():
    assert canon.encode_row(["1"], ["str"]) != canon.encode_row([1.0], ["f64"])
    assert canon.encode_row(["a", "b"], ["str", "str"]) != \
        canon.encode_row(["b", "a"], ["str", "str"])


def test_row_encoding_is_unambiguous_across_field_boundaries():
    # Length prefixes must prevent ("ab", "c") and ("a", "bc") colliding.
    assert canon.encode_row(["ab", "c"], ["str", "str"]) != \
        canon.encode_row(["a", "bc"], ["str", "str"])


def test_sort_key_is_byte_lexicographic():
    rows = [["b", "1"], ["a", "2"], ["a", "1"]]
    order = sorted(rows, key=lambda r: canon.sort_key(r, [0, 1]))
    assert order == [["a", "1"], ["a", "2"], ["b", "1"]]

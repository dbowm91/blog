import pytest
from app.base62 import encode, decode, ALPHABET, _DECODE_MAP


def test_encode_zero():
    assert encode(0) == "0"


def test_encode_one():
    assert encode(1) == "1"


def test_encode_known_values():
    assert encode(10) == "a"
    assert encode(35) == "z"
    assert encode(36) == "A"
    assert encode(61) == "Z"


def test_round_trip():
    for i in [0, 1, 10, 100, 1000, 9999, 100000]:
        assert decode(encode(i)) == i


def test_decode_invalid_char():
    with pytest.raises(ValueError):
        decode("!@#")


def test_decode_empty_string():
    assert decode("") == 0


def test_decode_map_consistency():
    for i, c in enumerate(ALPHABET):
        assert _DECODE_MAP[c] == i
    assert len(_DECODE_MAP) == 62


def test_encode_large_number():
    n = 123456789
    assert decode(encode(n)) == n


def test_decode_multichar():
    # "10" in base62 = 1*62 + 0 = 62
    assert decode("10") == 62

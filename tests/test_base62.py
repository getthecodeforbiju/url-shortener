"""
Unit tests for app/utils/base62.py
"""

import pytest
from app.utils.base62 import encode, decode, ALPHABET, BASE


class TestEncode:
    def test_zero(self):
        assert encode(0) == "0"

    def test_one(self):
        assert encode(1) == "1"

    def test_base_boundary(self):
        assert encode(BASE) == "10"

    def test_large_number(self):
        result = encode(123_456_789)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_only_valid_chars(self):
        for n in [0, 1, 10, 100, 999, 62 ** 3]:
            for ch in encode(n):
                assert ch in ALPHABET

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            encode(-1)

    def test_non_integer_raises(self):
        with pytest.raises((ValueError, TypeError)):
            encode("abc")  # type: ignore


class TestDecode:
    def test_zero(self):
        assert decode("0") == 0

    def test_one(self):
        assert decode("1") == 1

    def test_known_value(self):
        assert decode("10") == 62

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError, match="Invalid Base62 character"):
            decode("!!")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            decode("")


class TestRoundTrip:
    @pytest.mark.parametrize("n", [0, 1, 61, 62, 63, 999, 100_000, 2 ** 32])
    def test_round_trip(self, n):
        assert decode(encode(n)) == n

    def test_sequential_ids(self):
        """Simulate real DB IDs — all must round-trip correctly."""
        for i in range(1, 501):
            assert decode(encode(i)) == i

    def test_uniqueness(self):
        """Different IDs must never produce the same short code."""
        codes = [encode(i) for i in range(1, 1001)]
        assert len(codes) == len(set(codes))
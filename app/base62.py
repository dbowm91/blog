"""Base62 encoding/decoding for short URL generation.

Used by Post.short_code() to create compact share URLs (/s/<code>).
The alphabet is 0-9, a-z, A-Z (62 characters).
"""
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)
_DECODE_MAP = {c: i for i, c in enumerate(ALPHABET)}


def encode(n: int) -> str:
    """Encode an integer to base62 string."""
    if n == 0:
        return ALPHABET[0]
    result = []
    while n > 0:
        result.append(ALPHABET[n % BASE])
        n //= BASE
    return "".join(reversed(result))


def decode(s: str) -> int:
    """Decode a base62 string to integer."""
    n = 0
    for char in s:
        if char not in _DECODE_MAP:
            raise ValueError(f"Invalid base62 character: {char!r}")
        n = n * BASE + _DECODE_MAP[char]
    return n

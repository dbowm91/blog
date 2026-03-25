ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


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
        if char not in ALPHABET:
            raise ValueError(f"Invalid base62 character: {char!r}")
        n = n * BASE + ALPHABET.index(char)
    return n

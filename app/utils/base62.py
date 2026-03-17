"""
Base62 encoding utility.

Converts a positive integer (database row ID) into a short,
URL-safe alphanumeric string using characters: 0-9, A-Z, a-z

Flow:
    1. URL inserted into DB → gets numeric ID (e.g. 125)
    2. encode(125) → "2B"
    3. "2B" becomes the short_code
    4. decode("2B") → 125 (used for lookups)

Examples:
    encode(1)       → "1"
    encode(62)      → "10"
    encode(123456)  → "w7e"
    decode("w7e")   → 123456
"""

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET) #62

def encode(num: int) -> str:
    """Convert a non-negative integer to a Base62 string"""
    if not isinstance(num, int) or num < 0:
        raise ValueError(f"encode() expects a non-negotiable integer, got {num!r}")
    
    if num == 0:
        return ALPHABET[0]
    
    chars = []
    while num:
        num, remainder = divmod(num, BASE)
        chars.append(ALPHABET[remainder])
        
    return "".join(reversed(chars))

def decode(short_code: str) -> int:
    """Convert a Base62 string back to its integer value."""
    if not short_code or not isinstance(short_code, str):
        raise ValueError(f"decode() expects a non-empty string, got {short_code!r}")
    
    result = 0
    for char in short_code:
        idx = ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid Base62 characters: {char!r}")
        result = result * BASE + idx
        
    return result
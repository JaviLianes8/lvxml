"""Short, safe renderings of user values for error messages."""

from __future__ import annotations

# A message quotes at most this many characters of any value it names.
LIMIT = 40


def quote(value: object) -> str:
    """Return ``repr`` of `value`, cut to `LIMIT` characters of text with a marker.

    >>> quote("abc")
    "'abc'"
    >>> quote("x" * 100)
    "'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'... (100 characters)"
    """
    if isinstance(value, str) and len(value) > LIMIT:
        return f"{value[:LIMIT]!r}... ({len(value)} characters)"
    text = repr(value)
    return text if len(text) <= LIMIT + 2 else f"{text[:LIMIT]}..."

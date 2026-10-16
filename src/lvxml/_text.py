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


def segment(tag: str, name: str = "") -> str:
    """Return one step of an error location, such as ``DBL[x]``, with long parts cut.

    >>> segment("DBL", "x"), segment("Cluster")
    ('DBL[x]', 'Cluster')
    """
    tag = tag if len(tag) <= LIMIT else f"{tag[:LIMIT]}..."
    name = name if len(name) <= LIMIT else f"{name[:LIMIT]}..."
    return f"{tag}[{name}]" if name else tag


def join(parent: str, step: str) -> str:
    """Append `step` to the location `parent`."""
    return f"{parent}/{step}" if parent else step

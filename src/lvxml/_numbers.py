"""Scalar text in <Val>: parse it strictly and format it the way LabVIEW reads it back."""

from __future__ import annotations

import math
import re
import struct

from ._schema import ENUM_RANGES, INT_RANGES
from ._text import quote

# A period is the only decimal separator: LabVIEW does not localize this format. LabVIEW 2026
# allows spaces around a number, but not tabs or line breaks, and no plus sign on an integer.
# Each pattern matches in one pass (no nested repetition), so hostile text cannot make it slow.
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_FLOAT = re.compile(_NUMBER)
# LabVIEW 2026 reads these in any case and refuses "Infinity", "+NaN" and "-NaN".
_NON_FINITE = {"nan": math.nan, "inf": math.inf, "+inf": math.inf, "-inf": -math.inf}
_INT = re.compile(r"-?\d+")
# LabVIEW's run-time library formats a complex value as "<re> +<im> i".
_PART = rf"(?:{_NUMBER}|(?i:nan|[+-]?inf))"
_COMPLEX = re.compile(rf" *({_PART}) *\+ *({_PART}) *i *")
# Longer number text is refused before any conversion: no LabVIEW number needs it.
MAX_TEXT = 1000


def _short(text: str) -> None:
    if len(text) > MAX_TEXT:
        raise ValueError(f"number text of {len(text)} characters is longer than {MAX_TEXT}")


def parse_float(text: str) -> float:
    """Parse a float with a period decimal point; NaN, Inf, +Inf and -Inf in any case.

    >>> parse_float(" 1.5E3 "), parse_float("-inf")
    (1500.0, -inf)
    """
    _short(text)
    stripped = text.strip(" ")
    if stripped.lower() in _NON_FINITE:
        return _NON_FINITE[stripped.lower()]
    if not stripped.isascii() or not _FLOAT.fullmatch(stripped):
        hint = " (the decimal separator is always a period)" if "," in stripped else ""
        raise ValueError(f"invalid float value {quote(text)}{hint}")
    return float(stripped)


def parse_complex(text: str) -> complex:
    """Parse LabVIEW's ``re +im i`` complex text.

    >>> parse_complex("1.5 +-2 i")
    (1.5-2j)
    """
    _short(text)
    match = _COMPLEX.fullmatch(text) if text.isascii() else None
    if match is None:
        raise ValueError(f"invalid complex value {quote(text)}, expected '<re> +<im> i'")
    return complex(parse_float(match.group(1)), parse_float(match.group(2)))


def parse_int(text: str, tag: str) -> int:
    """Parse a decimal integer and check it fits `tag`'s range (an integer or enum tag)."""
    _short(text)
    stripped = text.strip(" ")
    if not stripped.isascii() or not _INT.fullmatch(stripped):
        raise ValueError(f"invalid integer value {quote(text)}")
    if len(stripped.lstrip("-").lstrip("0")) > 20:  # past every range; skip the conversion
        low, high = _range(tag)
        raise ValueError(f"{quote(stripped)} is out of range for {tag} ({low}..{high})")
    value = int(stripped, 10)
    check_range(value, tag)
    return value


def _range(tag: str) -> tuple[int, int]:
    return INT_RANGES[tag] if tag in INT_RANGES else ENUM_RANGES[tag]


def check_range(value: int, tag: str) -> None:
    low, high = _range(tag)
    if not low <= value <= high:
        shown = str(value) if value.bit_length() <= 128 else f"a {value.bit_length()}-bit integer"
        raise ValueError(f"{shown} is out of range for {tag} ({low}..{high})")


def parse_bool(text: str) -> bool:
    """Parse a Boolean ``<Val>`` as LabVIEW 2026 does: an unsigned decimal, true unless 0.

    >>> parse_bool("1"), parse_bool(" 0 "), parse_bool("2")
    (True, False, True)
    """
    _short(text)
    stripped = text.strip(" ")
    if not stripped.isascii() or not stripped.isdigit():
        raise ValueError(f"invalid boolean value {quote(text)}, expected unsigned digits")
    return stripped.strip("0") != ""


def format_float(value: float, tag: str) -> str:
    """Format a float with a period decimal point; non-finite as NaN, Inf or -Inf."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if tag in {"SGL", "CSG"}:
        try:
            struct.pack("<f", value)
        except OverflowError:
            raise ValueError(f"{value!r} does not fit single precision {tag}") from None
    return repr(float(value))


def format_complex(value: complex, tag: str) -> str:
    """Format a complex value as LabVIEW's ``re +im i``."""
    return f"{format_float(value.real, tag)} +{format_float(value.imag, tag)} i"

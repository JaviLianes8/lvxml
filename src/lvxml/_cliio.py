"""Input and output of the `lvxml` command: bounded lines, encodings, missing streams."""

from __future__ import annotations

import math
import sys
from typing import TextIO

from ._errors import LVXMLError
from ._numbers import format_float

# The longest line the command writes about a problem.
_LINE = 300


def say(stream: TextIO | None, line: str) -> None:
    """Write one line, cut to a bounded length, whatever the stream can encode."""
    if stream is None:
        return
    if len(line) > _LINE:
        line = line[: _LINE - 4] + " ..."
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(line.encode(encoding, "backslashreplace").decode(encoding) + "\n")
    stream.flush()


def read(path: str, encoding: str) -> str:
    if path == "-":
        if sys.stdin is None:
            raise LVXMLError("there is no standard input")
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as handle:
            data = handle.read()
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        where = "stdin" if path == "-" else "the file"
        raise LVXMLError(
            f"{where} is not valid {encoding} ({exc.reason}); try --encoding"
        ) from None


def write(text: str, output: str | None, encoding: str) -> None:
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError as exc:
        bad = exc.object[exc.start : min(exc.end, exc.start + 10)]
        raise LVXMLError(f"{bad!r} cannot be written as {encoding}; try --encoding utf-8") from None
    if output is not None:
        with open(output, "wb") as handle:
            handle.write(data)
    elif sys.stdout is not None:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def plain(value: object) -> object:
    """Make a value strict JSON: complex as {"re", "im"}, NaN and Inf as strings."""
    if isinstance(value, float) and not math.isfinite(value):
        return format_float(value, "DBL")
    if isinstance(value, complex):
        return {"re": plain(value.real), "im": plain(value.imag)}
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value

"""Consistency rules beyond the XSD's shape: counts that agree and values that parse."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ._errors import LVXMLError, cut
from ._node import Document, Node
from ._numbers import parse_bool, parse_complex, parse_float, parse_int
from ._parse import parse
from ._schema import COMPLEX_TAGS, ENUM_RANGES, FLOAT_TAGS, INT_RANGES
from ._text import join, quote, segment

_REFNUM = re.compile(r"0x[0-9A-Fa-f]+")

# An empty array with leading non-zero sizes (such as 1000x0) decodes to nested empty lists;
# more than this many is refused so a tiny input cannot demand unbounded memory.
MAX_EMPTY_ROWS = 100_000


def problems(node: Node) -> list[str]:
    """Return what is wrong with `node` itself, not looking inside its items."""
    found: list[str] = []
    try:
        _check_val(node)
    except ValueError as exc:
        found.append(str(exc))
    if node.tag == "Array":
        total = _total(node.dims)
        count = len(node.items)
        if total == 0 and count > 1:
            found.append(f"array Dimsize {_dims(node)} is empty but holds {count} elements")
        if total == 0 and _empty_rows(node.dims) > MAX_EMPTY_ROWS:
            found.append(f"empty array Dimsize {_dims(node)} needs over {MAX_EMPTY_ROWS} lists")
        elif total and count != total:
            found.append(f"array Dimsize {_dims(node)} needs {total} elements, found {count}")
        tags = {item.tag for item in node.items}
        if len(tags) > 1:
            found.append(f"array mixes element types {sorted(tags)}")
    if node.tag == "Cluster" and node.num_elts != len(node.items):
        found.append(f"cluster NumElts {node.num_elts} does not match {len(node.items)} elements")
    return found


def _total(dims: tuple[int, ...]) -> int:
    """The element count of `dims`, stopping once it passes any count an array can hold."""
    total = 1
    for dim in dims:
        total *= dim
        if total > 2**63:
            return 2**63 if 0 not in dims else 0
    return total


def _empty_rows(dims: tuple[int, ...]) -> int:
    rows, prefix = 0, 1
    for dim in dims[:-1]:
        if dim == 0:
            break
        prefix *= dim
        rows += prefix
        if rows > MAX_EMPTY_ROWS:
            break
    return rows


def _dims(node: Node) -> str:
    return "x".join(str(dim) for dim in node.dims)


def _check_val(node: Node) -> None:
    text = node.val if node.val is not None else ""
    if node.tag in FLOAT_TAGS:
        parse_float(text)
    elif node.tag in COMPLEX_TAGS:
        parse_complex(text)
    elif node.tag in INT_RANGES:
        parse_int(text, node.tag)
    elif node.tag == "Boolean":
        parse_bool(text)
    elif node.tag in ENUM_RANGES:
        index = parse_int(text, node.tag)
        if index >= len(node.choices):
            raise ValueError(f"enum index {index} is past its {len(node.choices)} choices")
    elif node.tag == "Refnum" and not _REFNUM.fullmatch(text.strip(" ")):
        # LabVIEW writes a refnum as 0x and hex digits and refuses a decimal one.
        raise ValueError(f"invalid refnum value {quote(text)}, expected 0x and hex digits")


def child_path(parent: str, node: Node) -> str:
    return join(parent, segment(node.tag, node.name))


def walk(node: Node, parent: str) -> Iterator[tuple[str, Node]]:
    """Yield every node under and including `node` with its path, depth first."""
    path = child_path(parent, node)
    yield path, node
    for item in node.items:
        yield from walk(item, path)


def validate(text: str | bytes | bytearray | memoryview) -> list[str]:
    """Return every problem found in LabVIEW XML `text`; an empty list means it is valid.

    A document that does not have the shape LVXMLSchema.xsd defines yields one problem,
    since its structure cannot be trusted further. A well-shaped one is then checked
    value by value: numbers that parse and fit their type, enum indexes inside the
    choice list, and ``NumElts`` and ``Dimsize`` that match the elements present.

    >>> validate("<I8><Name>n</Name><Val>300</Val></I8>")
    ['I8[n]: 300 is out of range for I8 (-128..127)']
    >>> validate("<I8><Name>n</Name><Val>-3</Val></I8>")
    []
    """
    try:
        document = parse(text)
    except LVXMLError as exc:
        return [str(exc)]
    found = document_problems(document)
    if document.wrapped and document.version is None:
        found.append("LVData: no <Version> header; LabVIEW's file reader refuses such a file")
    return found


def document_problems(document: Document) -> list[str]:
    """Return every value-level problem in an already parsed `document`."""
    root = "LVData" if document.wrapped else ""
    found: list[str] = []
    for top in document.values:
        for path, node in walk(top, root):
            found.extend(cut(f"{path}: {problem}") for problem in problems(node))
    return found

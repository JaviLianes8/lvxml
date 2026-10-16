"""Turn LabVIEW Flatten-To-XML text, or a parsed tree, into native Python values."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ._checks import child_path, problems
from ._errors import LVXMLError
from ._node import Node
from ._numbers import parse_bool, parse_complex, parse_float, parse_int
from ._parse import parse
from ._schema import COMPLEX_TAGS, ENUM_RANGES, FLOAT_TAGS, INT_RANGES, Value
from ._text import quote
from ._treejson import check_shape

T = TypeVar("T")


def from_lv_xml(text: str | bytes | bytearray | memoryview) -> Value:
    """Parse LabVIEW flattened XML into the Python value of its first value element.

    Inside an ``<LVData>`` file wrapper the ``<Version>`` header is skipped; use
    `from_lv_xml_all` when the file holds several values. Bytes are decoded by their XML
    declaration, or as UTF-8.

    >>> from_lv_xml("<I32><Name>count</Name><Val>-7</Val></I32>")
    -7
    >>> from_lv_xml("<Boolean><Name>on</Name><Val>1</Val></Boolean>")
    True
    """
    document = parse(text)
    if not document.values:
        raise LVXMLError("<LVData> holds no value")
    root = "LVData" if document.wrapped else ""
    return _guarded(lambda: _value(document.values[0], root))


def from_lv_xml_all(text: str | bytes | bytearray | memoryview) -> list[Value]:
    """Parse LabVIEW flattened XML into the Python values of every value element, in order.

    >>> from_lv_xml_all(
    ...     "<LVData><Version>26.3.1f1</Version>"
    ...     "<DBL><Name>a</Name><Val>0.5</Val></DBL>"
    ...     "<String><Name>b</Name><Val>x &amp; y</Val></String></LVData>"
    ... )
    [0.5, 'x & y']
    """
    document = parse(text)
    root = "LVData" if document.wrapped else ""
    return _guarded(lambda: [_value(node, root) for node in document.values])


def to_value(node: Node) -> Value:
    """Convert one typed `Node` into its Python value.

    Integers become ``int``, ``SGL``/``DBL``/``EXT`` ``float``, ``CSG``/``CDB``/``CXT``
    ``complex``, ``Boolean`` ``bool``; ``String``, ``Path``, ``DAQChannel`` and a
    ``Refnum``'s ``<Val>`` stay ``str``; an enum becomes its selected choice label. An
    ``Array`` becomes a list, nested once per dimension, and a ``Cluster`` a dict keyed by
    field name. ``LvVariant``, ``Timestamp``, ``WDT``, ``DynamicData``, ``DigitalData``
    and the waveform elements become the list of their items' values.

    >>> from lvxml import Node
    >>> to_value(Node("EW", "mode", val="1", choices=("Idle", "Run")))
    'Run'
    """
    if not isinstance(node, Node):
        raise TypeError(f"to_value takes a Node, not {type(node).__name__}")
    check_shape(node, "")
    return _guarded(lambda: _value(node, ""))


def _guarded(convert: Callable[[], T]) -> T:
    try:
        return convert()
    except RecursionError:
        raise LVXMLError("the tree is nested too deeply to convert") from None


def _value(node: Node, parent: str) -> Value:
    path = child_path(parent, node)
    found = problems(node)
    if found:
        raise LVXMLError(found[0], path)
    tag, text = node.tag, node.val if node.val is not None else ""
    if tag in FLOAT_TAGS:
        return parse_float(text)
    if tag in COMPLEX_TAGS:
        return parse_complex(text)
    if tag in INT_RANGES:
        return parse_int(text, tag)
    if tag == "Boolean":
        return parse_bool(text)
    if tag in ENUM_RANGES:
        return node.choices[parse_int(text, tag)]
    if tag == "Array":
        return _array(node, path)
    if tag == "Cluster":
        return _cluster(node, path)
    if node.items or node.val is None:
        return [_value(item, path) for item in node.items]
    return text


def _cluster(node: Node, path: str) -> dict[str, Value]:
    fields: dict[str, Value] = {}
    for item in node.items:
        if item.name in fields:
            raise LVXMLError(
                f"duplicate field name {quote(item.name)} cannot map to a dict; "
                "use lvxml.parse for positional access",
                path,
            )
        fields[item.name] = _value(item, path)
    return fields


def _array(node: Node, path: str) -> list[Value]:
    dims = node.dims
    if 0 in dims:
        for item in node.items:
            _value(item, path)  # the default element must still be a valid value
        return _empty(dims)
    flat = [_value(item, path) for item in node.items]
    return _reshape(flat, dims)


def _empty(dims: tuple[int, ...]) -> list[Value]:
    if dims[0] == 0 or len(dims) == 1:
        return []
    return [_empty(dims[1:]) for _ in range(dims[0])]


def _reshape(flat: list[Value], dims: tuple[int, ...]) -> list[Value]:
    if len(dims) == 1:
        return flat
    step = len(flat) // dims[0]
    return [_reshape(flat[i * step : (i + 1) * step], dims[1:]) for i in range(dims[0])]

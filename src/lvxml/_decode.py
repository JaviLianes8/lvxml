"""Turn LabVIEW Flatten-To-XML text into native Python values."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ._errors import LVXMLError
from ._schema import FLOAT_TAGS, INT_RANGES, Value


def from_lv_xml(text: str) -> Value:
    """Parse one LabVIEW flattened-XML element into a Python value."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise LVXMLError(f"invalid XML: {exc}") from exc
    return _decode(_unwrap(root))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _unwrap(element: ET.Element) -> ET.Element:
    if _local(element.tag) != "LVData":
        return element
    for child in element:
        if _local(child.tag) != "Version":
            return child
    raise LVXMLError("<LVData> holds no value")


def _decode(element: ET.Element) -> Value:
    tag = _local(element.tag)
    if tag == "Cluster":
        return _decode_cluster(element)
    if tag == "Array":
        return _decode_array(element)
    if tag in FLOAT_TAGS:
        return _to_float(element)
    if tag in INT_RANGES:
        return _to_int(element)
    if tag == "Boolean":
        return _to_bool(element)
    if tag == "String":
        return _val_text(element)
    raise LVXMLError(f"unknown LabVIEW type tag <{tag}>")


def _val_text(element: ET.Element) -> str:
    for child in element:
        if _local(child.tag) == "Val":
            return child.text or ""
    raise LVXMLError(f"<{_local(element.tag)}> has no <Val>")


def _name_of(element: ET.Element) -> str:
    for child in element:
        if _local(child.tag) == "Name":
            return child.text or ""
    return ""


def _to_float(element: ET.Element) -> float:
    raw = _val_text(element)
    try:
        return float(raw)
    except ValueError as exc:
        raise LVXMLError(f"invalid float value {raw!r}") from exc


def _to_int(element: ET.Element) -> int:
    raw = _val_text(element)
    try:
        return int(raw, 10)
    except ValueError as exc:
        raise LVXMLError(f"invalid integer value {raw!r}") from exc


def _to_bool(element: ET.Element) -> bool:
    raw = _val_text(element).strip().lower()
    if raw in {"1", "true"}:
        return True
    if raw in {"0", "false"}:
        return False
    raise LVXMLError(f"invalid boolean value {raw!r}")


def _decode_cluster(element: ET.Element) -> dict[str, Value]:
    fields: dict[str, Value] = {}
    for child in element:
        if _local(child.tag) in {"Name", "NumElts"}:
            continue
        fields[_name_of(child)] = _decode(child)
    return fields


def _decode_array(element: ET.Element) -> list[Value]:
    dimsize: int | None = None
    items: list[Value] = []
    for child in element:
        name = _local(child.tag)
        if name == "Name":
            continue
        if name == "Dimsize":
            if dimsize is not None:
                raise LVXMLError("multi-dimensional arrays are not supported")
            dimsize = _dim(child)
            continue
        items.append(_decode(child))
    if dimsize is None:
        raise LVXMLError("<Array> has no <Dimsize>")
    if dimsize == 0:
        return []
    if len(items) != dimsize:
        raise LVXMLError(f"array Dimsize {dimsize} does not match {len(items)} elements")
    return items


def _dim(element: ET.Element) -> int:
    try:
        return int(element.text or "0", 10)
    except ValueError as exc:
        raise LVXMLError(f"invalid Dimsize {element.text!r}") from exc

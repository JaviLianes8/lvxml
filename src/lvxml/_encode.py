"""Render native Python values as LabVIEW Unflatten-From-XML text."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ._errors import LVXMLError
from ._schema import FLOAT_TAGS, INT_RANGES, Array, Cluster, Schema, Value


def to_lv_xml(value: Value, schema: Schema, name: str = "") -> str:
    """Render `value` as LabVIEW flattened XML matching `schema`."""
    element = _encode(value, schema, name)
    ET.indent(element)
    return ET.tostring(element, encoding="unicode")


def _encode(value: Value, schema: Schema, name: str) -> ET.Element:
    if isinstance(schema, Array):
        return _encode_array(value, schema, name)
    if isinstance(schema, Cluster):
        return _encode_cluster(value, schema, name)
    return _encode_scalar(value, schema, name)


def _named(tag: str, name: str) -> ET.Element:
    element = ET.Element(tag)
    label = ET.SubElement(element, "Name")
    if name:
        label.text = name
    return element


def _encode_scalar(value: Value, tag: str, name: str) -> ET.Element:
    element = _named(tag, name)
    ET.SubElement(element, "Val").text = _scalar_text(value, tag)
    return element


def _scalar_text(value: Value, tag: str) -> str:
    if tag in FLOAT_TAGS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LVXMLError(f"{tag} expects a number, got {type(value).__name__}")
        return repr(float(value))
    if tag in INT_RANGES:
        if isinstance(value, bool) or not isinstance(value, int):
            raise LVXMLError(f"{tag} expects an int, got {type(value).__name__}")
        low, high = INT_RANGES[tag]
        if not low <= value <= high:
            raise LVXMLError(f"{value} is out of range for {tag}")
        return str(value)
    if tag == "Boolean":
        if not isinstance(value, bool):
            raise LVXMLError(f"Boolean expects a bool, got {type(value).__name__}")
        return "1" if value else "0"
    if tag == "String":
        if not isinstance(value, str):
            raise LVXMLError(f"String expects a str, got {type(value).__name__}")
        return value
    raise LVXMLError(f"unknown LabVIEW type tag {tag!r}")


def _encode_cluster(value: Value, schema: Cluster, name: str) -> ET.Element:
    if not isinstance(value, dict):
        raise LVXMLError(f"Cluster expects a dict, got {type(value).__name__}")
    extra = set(value) - set(schema.fields)
    if extra:
        raise LVXMLError(f"cluster value has unknown fields {sorted(extra)}")
    element = _named("Cluster", name)
    ET.SubElement(element, "NumElts").text = str(len(schema.fields))
    for field_name, field_schema in schema.fields.items():
        if field_name not in value:
            raise LVXMLError(f"missing cluster field {field_name!r}")
        element.append(_encode(value[field_name], field_schema, field_name))
    return element


def _encode_array(value: Value, schema: Array, name: str) -> ET.Element:
    if not isinstance(value, list):
        raise LVXMLError(f"Array expects a list, got {type(value).__name__}")
    element = _named("Array", name)
    ET.SubElement(element, "Dimsize").text = str(len(value))
    items: list[Value] = value if value else [_default(schema.element)]
    for item in items:
        element.append(_encode(item, schema.element, ""))
    return element


def _default(schema: Schema) -> Value:
    if isinstance(schema, Array):
        return []
    if isinstance(schema, Cluster):
        return {name: _default(sub) for name, sub in schema.fields.items()}
    if schema in FLOAT_TAGS:
        return 0.0
    if schema in INT_RANGES:
        return 0
    if schema == "Boolean":
        return False
    if schema == "String":
        return ""
    raise LVXMLError(f"unknown LabVIEW type tag {schema!r}")

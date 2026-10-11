"""Render native Python values as LabVIEW Unflatten-From-XML text, driven by a schema."""

from __future__ import annotations

from ._dump import dump
from ._errors import LVXMLError
from ._node import Node
from ._numbers import check_range, format_complex, format_float
from ._schema import (
    COMPLEX_TAGS,
    FLOAT_TAGS,
    INT_RANGES,
    TEXT_TAGS,
    Array,
    Cluster,
    LVEnum,
    Schema,
    Value,
)


def to_lv_xml(value: Value, schema: Schema, name: str = "") -> str:
    """Render `value` as LabVIEW flattened XML matching `schema`, indented for reading."""
    return dump(to_node(value, schema, name), newline="\n", indent="  ")


def to_node(value: Value, schema: Schema, name: str = "") -> Node:
    """Build the typed `Node` for `value` under `schema`, checking every type and range."""
    try:
        return _encode(value, schema, name, name or "value")
    except RecursionError:
        raise LVXMLError("the value is nested too deeply to write") from None


def _encode(value: Value, schema: Schema, name: str, path: str) -> Node:
    if isinstance(schema, Array):
        return _encode_array(value, schema, name, path)
    if isinstance(schema, Cluster):
        return _encode_cluster(value, schema, name, path)
    if not isinstance(schema, (str, LVEnum)):
        kind = type(schema).__name__
        raise TypeError(f"a schema is a tag string, Array, Cluster or LVEnum, not {kind}")
    if isinstance(schema, LVEnum):
        return Node(
            schema.tag, name, val=str(_enum_index(value, schema, path)), choices=schema.choices
        )
    return Node(schema, name, val=_scalar_text(value, schema, path))


def _kind(value: Value) -> str:
    return type(value).__name__


def _scalar_text(value: Value, tag: str, path: str) -> str:
    try:
        if tag in FLOAT_TAGS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise LVXMLError(f"{tag} expects a number, got {_kind(value)}", path)
            return format_float(float(value), tag)
        if tag in COMPLEX_TAGS:
            if isinstance(value, bool) or not isinstance(value, (int, float, complex)):
                raise LVXMLError(f"{tag} expects a number, got {_kind(value)}", path)
            return format_complex(complex(value), tag)
        if tag in INT_RANGES:
            if isinstance(value, bool) or not isinstance(value, int):
                raise LVXMLError(f"{tag} expects an int, got {_kind(value)}", path)
            check_range(value, tag)
            return str(value)
    except (ValueError, OverflowError) as exc:
        if isinstance(exc, LVXMLError):
            raise
        raise LVXMLError(str(exc), path) from exc
    if tag == "Boolean":
        if not isinstance(value, bool):
            raise LVXMLError(f"Boolean expects a bool, got {_kind(value)}", path)
        return "1" if value else "0"
    if tag in TEXT_TAGS:
        if not isinstance(value, str):
            raise LVXMLError(f"{tag} expects a str, got {_kind(value)}", path)
        return value
    raise LVXMLError(f"unknown or unsupported LabVIEW type tag {tag!r}", path)


def _enum_index(value: Value, schema: LVEnum, path: str) -> int:
    if isinstance(value, str):
        if value not in schema.choices:
            raise LVXMLError(f"{value!r} is not one of the choices {list(schema.choices)}", path)
        return schema.choices.index(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LVXMLError(f"{schema.tag} expects a choice label or index, got {_kind(value)}", path)
    if not 0 <= value < len(schema.choices):
        raise LVXMLError(f"enum index {value} is outside 0..{len(schema.choices) - 1}", path)
    return value


def _encode_cluster(value: Value, schema: Cluster, name: str, path: str) -> Node:
    if not isinstance(value, dict):
        raise LVXMLError(f"Cluster expects a dict, got {_kind(value)}", path)
    extra = set(value) - set(schema.fields)
    if extra:
        raise LVXMLError(f"cluster value has unknown fields {sorted(extra)}", path)
    items: list[Node] = []
    for field_name, field_schema in schema.fields.items():
        if field_name not in value:
            raise LVXMLError(f"missing cluster field {field_name!r}", path)
        items.append(_encode(value[field_name], field_schema, field_name, f"{path}.{field_name}"))
    return Node("Cluster", name, num_elts=len(items), items=tuple(items))


def _encode_array(value: Value, schema: Array, name: str, path: str) -> Node:
    dims: list[int] = []
    flat = _flatten(value, schema.ndim, dims, path)
    # An empty array still carries one default element, so the element type is visible.
    if not flat:
        flat = [_default(schema.element)]
    items = tuple(_encode(item, schema.element, "", f"{path}[{i}]") for i, item in enumerate(flat))
    return Node("Array", name, dims=tuple(dims), items=items)


def _flatten(value: Value, ndim: int, dims: list[int], path: str) -> list[Value]:
    """Flatten a nested list row-major, recording its shape and rejecting ragged rows."""
    if not isinstance(value, list):
        raise LVXMLError(f"Array expects a list, got {_kind(value)}", path)
    dims.append(len(value))
    if ndim == 1:
        return list(value)
    if not value:
        dims.extend([0] * (ndim - 1))
        return []
    rows: list[list[Value]] = []
    for index, row in enumerate(value):
        row_dims: list[int] = []
        rows.append(_flatten(row, ndim - 1, row_dims, f"{path}[{index}]"))
        if index == 0:
            dims.extend(row_dims)
        elif row_dims != dims[len(dims) - len(row_dims) :]:
            raise LVXMLError(f"ragged array: row {index} has shape {row_dims}", path)
    return [item for row in rows for item in row]


def _default(schema: Schema) -> Value:
    if isinstance(schema, Array):
        return []
    if isinstance(schema, Cluster):
        return {name: _default(sub) for name, sub in schema.fields.items()}
    if isinstance(schema, LVEnum):
        return schema.choices[0]
    if schema in FLOAT_TAGS:
        return 0.0
    if schema in COMPLEX_TAGS:
        return 0j
    if schema in INT_RANGES:
        return 0
    if schema == "Boolean":
        return False
    if schema in TEXT_TAGS:
        return ""
    raise LVXMLError(f"unknown or unsupported LabVIEW type tag {schema!r}")

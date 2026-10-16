"""Check a tree's shape against the schema and convert it to and from JSON-ready dicts."""

from __future__ import annotations

from ._errors import LVXMLError
from ._node import LVDATA_NAMESPACE, Document, Node
from ._parse import MAX_DEPTH
from ._schema import ARRAY_ITEM_TAGS, CLUSTERED_TAGS, ENUM_RANGES, SIMPLE_TAGS, VALUE_TAGS
from ._text import join, quote, segment

_EXTRA_ORDER = ("RefKind", "RefType", "ActiveXType.GUID", "ActiveXType.Name", "DotNetType.Name")
_NEEDS = {"RefType": "RefKind", "ActiveXType.Name": "ActiveXType.GUID"}
_FIELDS = ("name", "val", "choices", "dims", "num_elts", "items", "extra")


def check_shape(node: Node, path: str, depth: int = 1) -> None:
    """Raise unless `node` only uses the parts LVXMLSchema.xsd gives its tag."""
    tag = node.tag
    here = join(path, segment(tag, node.name))
    if depth > MAX_DEPTH:
        raise LVXMLError(f"nesting deeper than {MAX_DEPTH} levels is not supported", path)
    if tag not in VALUE_TAGS:
        raise LVXMLError(f"unknown LabVIEW type tag {quote(tag)}", here)
    used = {f for f in _FIELDS[1:] if getattr(node, f) not in (None, ())}
    allowed = _allowed(tag)
    if used - allowed or (allowed & {"val", "num_elts", "dims", "choices"}) - used:
        raise LVXMLError(f"<{tag}> takes {sorted(allowed)}, got {sorted(used)}", here)
    if (node.num_elts or 0) < 0 or any(dim < 0 for dim in node.dims):
        raise LVXMLError("NumElts and Dimsize cannot be negative", here)
    keys = [key for key, _ in node.extra]
    order = [_EXTRA_ORDER.index(k) if k in _EXTRA_ORDER else -1 for k in keys]
    if -1 in order or order != sorted(set(order)):
        raise LVXMLError(f"Refnum fields must be a subset of {list(_EXTRA_ORDER)} in order", here)
    for key, needed in _NEEDS.items():
        if key in keys and needed not in keys:
            raise LVXMLError(f"Refnum field {key} needs {needed}", here)
    members = frozenset({"Cluster"}) if tag in CLUSTERED_TAGS else _members(tag)
    for item in node.items:
        if item.tag not in members:
            raise LVXMLError(f"<{segment(item.tag)}> is not allowed inside <{tag}>", here)
        check_shape(item, here, depth + 1)


def _allowed(tag: str) -> set[str]:
    if tag in SIMPLE_TAGS:
        return {"val"}
    if tag in ENUM_RANGES:
        return {"val", "choices"}
    if tag == "Refnum":
        return {"val", "extra"}
    if tag == "Array":
        return {"dims", "items"}
    if tag == "Cluster":
        return {"num_elts", "items"}
    return {"items"}


def _members(tag: str) -> frozenset[str]:
    return ARRAY_ITEM_TAGS if tag == "Array" else VALUE_TAGS


def node_to_dict(node: Node) -> dict[str, object]:
    data: dict[str, object] = {"tag": node.tag}
    if node.tag != "Version":
        data["name"] = node.name
    if node.val is not None:
        data["val"] = node.val
    if node.choices:
        data["choices"] = list(node.choices)
    if node.dims:
        data["dims"] = list(node.dims)
    if node.num_elts is not None:
        data["num_elts"] = node.num_elts
    if node.extra:
        data["extra"] = [list(pair) for pair in node.extra]
    if node.items or node.tag in {"Array", "Cluster", "LvVariant"} | CLUSTERED_TAGS:
        data["items"] = [node_to_dict(item) for item in node.items]
    return data


def document_to_dict(document: Document) -> dict[str, object]:
    return {
        "wrapped": document.wrapped,
        "namespace": document.namespace,
        "items": [node_to_dict(node) for node in document.items],
    }


def _get(data: dict[str, object], key: str, kind: type, path: str) -> object:
    value = data.get(key)
    if value is not None and (
        not isinstance(value, kind) or isinstance(value, bool) != (kind is bool)
    ):
        raise LVXMLError(f"field {quote(key)} must be {kind.__name__}", path)
    return value


def _strings(value: object, key: str, path: str) -> tuple[str, ...]:
    items = value if isinstance(value, list) else []
    if not all(isinstance(item, str) for item in items):
        raise LVXMLError(f"field {quote(key)} must be a list of strings", path)
    return tuple(str(item) for item in items)


def node_from_dict(data: object, path: str, depth: int = 1) -> Node:
    if depth > MAX_DEPTH:
        raise LVXMLError(f"nesting deeper than {MAX_DEPTH} levels is not supported", path)
    if not isinstance(data, dict):
        raise LVXMLError("a node must be an object", path)
    unknown = set(data) - {"tag", *_FIELDS}
    if unknown:
        raise LVXMLError(f"unknown node fields {quote(sorted(unknown))}", path)
    tag = _get(data, "tag", str, path)
    if not isinstance(tag, str):
        raise LVXMLError("a node needs a string 'tag'", path)
    here = join(path, segment(tag))
    if tag != "Version" and "name" not in data:
        raise LVXMLError("a node needs a 'name' (use \"\" for an unnamed one)", here)
    dims = _get(data, "dims", list, here) or []
    assert isinstance(dims, list)
    if not all(isinstance(d, int) and not isinstance(d, bool) and d >= 0 for d in dims):
        raise LVXMLError("field 'dims' must be a list of non-negative ints", here)
    extra = _get(data, "extra", list, here) or []
    assert isinstance(extra, list)
    pairs = tuple(_strings(pair, "extra", here) for pair in extra)
    if any(len(pair) != 2 for pair in pairs):
        raise LVXMLError("field 'extra' must hold [key, text] pairs", here)
    items = _get(data, "items", list, here) or []
    assert isinstance(items, list)
    num_elts = _get(data, "num_elts", int, here)
    name, val = _get(data, "name", str, here), _get(data, "val", str, here)
    return Node(
        tag,
        name=name if isinstance(name, str) else "",
        val=val if isinstance(val, str) else None,
        choices=_strings(_get(data, "choices", list, here), "choices", here),
        dims=tuple(int(d) for d in dims),
        num_elts=num_elts if isinstance(num_elts, int) else None,
        items=tuple(node_from_dict(item, here, depth + 1) for item in items),
        extra=tuple((pair[0], pair[1]) for pair in pairs),
    )


def document_from_dict(data: object) -> Document:
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise LVXMLError("a document must be an object with an 'items' list")
    unknown = set(data) - {"wrapped", "namespace", "items"}
    if unknown:
        raise LVXMLError(f"unknown document fields {quote(sorted(unknown))}")
    wrapped, namespace = data.get("wrapped", True), data.get("namespace", LVDATA_NAMESPACE)
    if not isinstance(wrapped, bool) or not (namespace is None or isinstance(namespace, str)):
        raise LVXMLError("'wrapped' must be a bool and 'namespace' a string or null")
    root = "LVData" if wrapped else ""
    nodes = tuple(node_from_dict(item, root) for item in data["items"])
    for node in nodes:
        if node.tag == "Version" and wrapped and node.name == "" and node.val is not None:
            if node.items or node.choices or node.dims or node.extra or node.num_elts is not None:
                raise LVXMLError("a Version entry only takes 'val'", root)
            continue
        check_shape(node, root)
    if not wrapped and len(nodes) != 1:
        raise LVXMLError("a bare document holds exactly one value")
    return Document(nodes, wrapped=wrapped, namespace=namespace)

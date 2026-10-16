"""Field types of `Node` and `Document`, checked when one is built."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._node import Document, Node


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _tuple(owner: object, field: str, value: object) -> tuple[object, ...]:
    """Store a list or tuple field as a tuple, refusing text and other types."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list)):
        raise TypeError(f"{field} must be a tuple, got {type(value).__name__}")
    stored = tuple(value)
    object.__setattr__(owner, field, stored)
    return stored


def check_node(node: Node) -> None:
    """Raise `TypeError` unless every field of `node` has its documented type."""
    from ._node import Node

    if not isinstance(node.tag, str) or not isinstance(node.name, str):
        raise TypeError("Node tag and name must be str")
    if node.val is not None and not isinstance(node.val, str):
        raise TypeError(f"Node val must be str or None, got {type(node.val).__name__}")
    if node.num_elts is not None and not _int(node.num_elts):
        raise TypeError(f"Node num_elts must be int or None, got {type(node.num_elts).__name__}")
    if not all(isinstance(choice, str) for choice in _tuple(node, "choices", node.choices)):
        raise TypeError("Node choices must hold str labels")
    if not all(_int(dim) for dim in _tuple(node, "dims", node.dims)):
        raise TypeError("Node dims must hold int sizes")
    if not all(isinstance(item, Node) for item in _tuple(node, "items", node.items)):
        raise TypeError("Node items must hold Node objects")
    pairs = _tuple(node, "extra", node.extra)
    for pair in pairs:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise TypeError("Node extra must hold (key, text) pairs")
        if not all(isinstance(part, str) for part in pair):
            raise TypeError("Node extra keys and texts must be str")
    object.__setattr__(node, "extra", tuple(tuple(pair) for pair in pairs))  # type: ignore[arg-type]


def check_document(document: Document) -> None:
    """Raise `TypeError` unless every field of `document` has its documented type."""
    from ._node import Node

    if not all(isinstance(item, Node) for item in _tuple(document, "items", document.items)):
        raise TypeError("Document items must hold Node objects")
    if not isinstance(document.wrapped, bool):
        raise TypeError(f"Document wrapped must be a bool, got {type(document.wrapped).__name__}")
    if document.namespace is not None and not isinstance(document.namespace, str):
        raise TypeError("Document namespace must be str or None")

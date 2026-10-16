"""Read LabVIEW XML text into the typed tree, enforcing the shape LVXMLSchema.xsd defines."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ._errors import LVXMLError
from ._load import decode, load
from ._node import Document, Node
from ._schema import (
    ARRAY_ITEM_TAGS,
    CLUSTERED_TAGS,
    ENUM_RANGES,
    SIMPLE_TAGS,
    VALUE_TAGS,
)

# Deeper nesting than this is refused rather than exhausting the interpreter's stack.
MAX_DEPTH = 100


def parse(text: str | bytes) -> Document:
    """Parse LabVIEW Flatten-To-XML, bare or inside ``<LVData>``, into a `Document`.

    Bytes are decoded by the encoding their XML declaration names, or as UTF-8.
    """
    root = load(decode(text))
    tag, namespace = _split(root.tag)
    for element in root.iter():
        if _split(element.tag)[1] != namespace:
            where = _split(element.tag)[0]
            raise LVXMLError(f"<{where}> is not in the root element's namespace {namespace!r}")
    _no_attributes(root, tag)
    if tag != "LVData":
        return Document((_node(root, VALUE_TAGS, "", 1),), wrapped=False, namespace=namespace)
    _no_text(root.text, "LVData")
    items: list[Node] = []
    for child in root:
        _no_text(child.tail, "LVData")
        if _split(child.tag)[0] == "Version":
            items.append(Node("Version", val=_leaf(child, "LVData/Version")))
        else:
            items.append(_node(child, VALUE_TAGS, "LVData", 1))
    return Document(tuple(items), wrapped=True, namespace=namespace)


def _split(tag: str) -> tuple[str, str | None]:
    if tag.startswith("{"):
        namespace, local = tag[1:].split("}", 1)
        return local, namespace
    return tag, None


def _no_attributes(element: ET.Element, path: str) -> None:
    if element.attrib:
        raise LVXMLError(f"unexpected attributes {sorted(element.attrib)}", path)


def _no_text(text: str | None, path: str) -> None:
    if text is not None and text.strip():
        raise LVXMLError(f"unexpected text {text.strip()[:40]!r}", path)


def _leaf(element: ET.Element, path: str) -> str:
    _no_attributes(element, path)
    if len(element):
        raise LVXMLError("expected text only, found child elements", path)
    return element.text or ""


class _Children:
    """Walk an element's children in order, as the schema's xsd:sequence requires."""

    def __init__(self, element: ET.Element, path: str, depth: int = 0) -> None:
        _no_text(element.text, path)
        self.depth = depth
        self.kids = list(element)
        for kid in self.kids:
            _no_text(kid.tail, path)
        self.pos = 0
        self.path = path

    def peek(self) -> str | None:
        return _split(self.kids[self.pos].tag)[0] if self.pos < len(self.kids) else None

    def take(self, tag: str) -> str:
        if self.peek() != tag:
            found = f"<{self.peek()}>" if self.peek() else "the end of the element"
            raise LVXMLError(f"expected <{tag}>, found {found}", self.path)
        self.pos += 1
        return _leaf(self.kids[self.pos - 1], f"{self.path}/{tag}")

    def take_all(self, tag: str) -> list[str]:
        values = [self.take(tag)]
        while self.peek() == tag:
            values.append(self.take(tag))
        return values

    def rest(self, allowed: frozenset[str]) -> tuple[Node, ...]:
        nodes = tuple(_node(k, allowed, self.path, self.depth + 1) for k in self.kids[self.pos :])
        self.pos = len(self.kids)
        return nodes

    def end(self) -> None:
        if self.pos < len(self.kids):
            raise LVXMLError(f"unexpected <{self.peek()}>", self.path)


def _node(element: ET.Element, allowed: frozenset[str], parent: str, depth: int) -> Node:
    tag = _split(element.tag)[0]
    here = f"{parent}/{tag}" if parent else tag
    if depth > MAX_DEPTH:
        raise LVXMLError(f"nesting deeper than {MAX_DEPTH} levels is not supported", here)
    if tag not in allowed:
        where = f"inside <{parent.rsplit('/', 1)[-1]}>" if parent else "as a root element"
        raise LVXMLError(f"<{tag}> is not allowed {where} by LVXMLSchema.xsd", here)
    _no_attributes(element, here)
    kids = _Children(element, here, depth)
    name = kids.take("Name")
    kids.path = f"{here}[{name}]" if name else here
    node = _body(tag, name, kids)
    kids.end()
    return node


def _body(tag: str, name: str, kids: _Children) -> Node:
    if tag in SIMPLE_TAGS:
        return Node(tag, name, val=kids.take("Val"))
    if tag in ENUM_RANGES:
        choices = tuple(kids.take_all("Choice"))
        return Node(tag, name, val=kids.take("Val"), choices=choices)
    if tag == "Refnum":
        # LabVIEW 2026 writes RefKind and RefType before <Val>; the XSD puts them after it.
        early = _kinds(kids)
        val = kids.take("Val")
        return Node(tag, name, val=val, extra=early + _refnum_extra(kids, not early))
    if tag == "Array":
        dims = tuple(_count(text, f"{kids.path}/Dimsize") for text in kids.take_all("Dimsize"))
        return Node(tag, name, dims=dims, items=kids.rest(ARRAY_ITEM_TAGS))
    if tag == "Cluster":
        num_elts = _count(kids.take("NumElts"), f"{kids.path}/NumElts")
        return Node(tag, name, num_elts=num_elts, items=kids.rest(VALUE_TAGS))
    if tag in CLUSTERED_TAGS:
        return Node(tag, name, items=kids.rest(frozenset({"Cluster"})))
    return Node(tag, name, items=kids.rest(VALUE_TAGS))  # LvVariant


def _kinds(kids: _Children) -> tuple[tuple[str, str], ...]:
    if kids.peek() != "RefKind":
        return ()
    kind = (("RefKind", kids.take("RefKind")),)
    return kind + ((("RefType", kids.take("RefType")),) if kids.peek() == "RefType" else ())


def _refnum_extra(kids: _Children, kinds: bool) -> tuple[tuple[str, str], ...]:
    extra: list[tuple[str, str]] = list(_kinds(kids)) if kinds else []
    for group, fields in (("ActiveXType", ("GUID", "Name")), ("DotNetType", ("Name",))):
        if kids.peek() != group:
            continue
        sub = _Children(kids.kids[kids.pos], f"{kids.path}/{group}")
        _no_attributes(kids.kids[kids.pos], sub.path)
        kids.pos += 1
        for index, field in enumerate(fields):
            if index == 0 or sub.peek() == field:
                extra.append((f"{group}.{field}", sub.take(field)))
        sub.end()
    return tuple(extra)


def _count(text: str, path: str) -> int:
    stripped = text.strip()
    if not stripped.isdigit() or not stripped.isascii():
        raise LVXMLError(f"expected a non-negative integer, got {text!r}", path)
    return int(stripped)

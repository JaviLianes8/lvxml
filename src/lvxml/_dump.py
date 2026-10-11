"""Write the typed tree back as text, in the layout LabVIEW's own XML writer uses."""

from __future__ import annotations

import re

from ._errors import LVXMLError
from ._node import Document, Node
from ._treejson import check_shape

# The declaration LabVIEW's XML file writer emits before <LVData>.
DECLARATION = "<?xml version='1.0' standalone='yes' ?>"

# Characters XML 1.0 cannot carry at all, even escaped.
_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def dump(
    tree: Document | Node,
    *,
    newline: str = "\r\n",
    indent: str = "",
    declaration: bool | None = None,
) -> str:
    """Serialize a `Document` or a single `Node` as LabVIEW XML.

    The defaults reproduce LabVIEW's file writer: one element per line, CRLF line breaks,
    no indentation, empty elements written as ``<Name></Name>``, only ``&``, ``<`` and
    ``>`` escaped, and no line break after the last element. `declaration` defaults to
    true for an ``<LVData>`` document and false otherwise. A `Node` is written bare, as
    Flatten To XML outputs it.
    """
    document = tree if isinstance(tree, Document) else Document((tree,), False, None)
    if not document.wrapped and len(document.items) != 1:
        raise LVXMLError("a bare document holds exactly one value; set wrapped=True")
    root = "LVData" if document.wrapped else ""
    for node in document.items:
        if node.tag == "Version" and document.wrapped:
            if node != Node("Version", val=node.val) or node.val is None:
                raise LVXMLError("a Version node only takes a val", root)
        else:
            check_shape(node, root)
    lines: list[str] = []
    if declaration if declaration is not None else document.wrapped:
        lines.append(DECLARATION)
    xmlns = f' xmlns="{_escape(document.namespace, attr=True)}"' if document.namespace else ""
    if document.wrapped:
        lines.append(f"<LVData{xmlns}>")
        for node in document.items:
            _write(node, lines, indent, 1 if indent else 0, "")
        lines.append("</LVData>")
    else:
        _write(document.items[0], lines, indent, 0, xmlns)
    return newline.join(lines)


def _escape(text: str, attr: bool = False) -> str:
    bad = _ILLEGAL.search(text)
    if bad:
        raise LVXMLError(f"character U+{ord(bad.group()):04X} cannot be written in XML")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.replace('"', "&quot;") if attr else text


def _leaf(tag: str, text: str, pad: str) -> str:
    return f"{pad}<{tag}>{_escape(text)}</{tag}>"


def _write(node: Node, lines: list[str], indent: str, depth: int, xmlns: str) -> None:
    pad = indent * depth
    inner = indent * (depth + 1)
    if node.tag == "Version":
        lines.append(_leaf("Version", node.val or "", pad))
        return
    lines.append(f"{pad}<{node.tag}{xmlns}>")
    lines.append(_leaf("Name", node.name, inner))
    lines.extend(_leaf("Choice", choice, inner) for choice in node.choices)
    if node.val is not None:
        lines.append(_leaf("Val", node.val, inner))
    _write_extra(node.extra, lines, inner, indent)
    lines.extend(_leaf("Dimsize", str(dim), inner) for dim in node.dims)
    if node.num_elts is not None:
        lines.append(_leaf("NumElts", str(node.num_elts), inner))
    for item in node.items:
        _write(item, lines, indent, depth + 1, "")
    lines.append(f"{pad}</{node.tag}>")


def _write_extra(
    extra: tuple[tuple[str, str], ...], lines: list[str], pad: str, indent: str
) -> None:
    open_group = ""
    for key, text in extra:
        group, _, field = key.rpartition(".")
        if group != open_group:
            if open_group:
                lines.append(f"{pad}</{open_group}>")
            if group:
                lines.append(f"{pad}<{group}>")
            open_group = group
        lines.append(_leaf(field, text, pad + indent if group else pad))
    if open_group:
        lines.append(f"{pad}</{open_group}>")

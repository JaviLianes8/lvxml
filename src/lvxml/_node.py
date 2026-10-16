"""The lossless typed tree: one `Node` per LabVIEW element, wrapped in a `Document`."""

from __future__ import annotations

from dataclasses import dataclass

from ._fields import check_document, check_node

# The namespace LabVIEW's XML file writer puts on <LVData>.
LVDATA_NAMESPACE = "http://www.ni.com/LVData"


@dataclass(frozen=True)
class Node:
    """One LabVIEW value element, keeping every piece of the XML.

    `val` holds the raw ``<Val>`` text exactly as written (``None`` for containers),
    `choices` an enum's ``<Choice>`` labels, `dims` an array's ``<Dimsize>`` values,
    `num_elts` a cluster's ``<NumElts>``, and `items` the child value elements of an
    array, cluster, variant, timestamp or waveform. `extra` keeps a ``Refnum``'s optional
    ``RefKind``, ``RefType``, ``ActiveXType.GUID``, ``ActiveXType.Name`` and
    ``DotNetType.Name`` fields in document order. A ``Version`` header inside
    ``<LVData>`` is a node with tag ``"Version"`` and its text in `val`. Fields are type
    checked when a node is built (`TypeError`), lists are stored as tuples, and whether the
    fields suit the tag is checked by `dump` and `to_value` (`LVXMLError`).

    >>> node = Node("DBL", "x", val="1.5")
    >>> Node.from_dict(node.to_dict()) == node
    True
    """

    tag: str
    name: str = ""
    val: str | None = None
    choices: tuple[str, ...] = ()
    dims: tuple[int, ...] = ()
    num_elts: int | None = None
    items: tuple[Node, ...] = ()
    extra: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        check_node(self)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready dict that `Node.from_dict` turns back into this node."""
        from ._treejson import node_to_dict

        return node_to_dict(self)

    @staticmethod
    def from_dict(data: object) -> Node:
        """Build a node from the dict shape `to_dict` produces, checking every field."""
        from ._treejson import node_from_dict

        return node_from_dict(data, "")


@dataclass(frozen=True)
class Document:
    """A parsed LabVIEW XML document.

    `wrapped` is true for the ``<LVData>`` file form, whose `items` may include
    ``Version`` nodes; otherwise the document is the bare output of Flatten To XML and
    `items` holds exactly one node. `namespace` is the default XML namespace of the root
    element, or ``None`` when it has none (`LVDATA_NAMESPACE` is LabVIEW's).

    >>> document = Document((Node("Version", val="26.3.1f1"), Node("I8", "n", val="1")))
    >>> document.version, [node.tag for node in document.values]
    ('26.3.1f1', ['I8'])
    >>> document.namespace == LVDATA_NAMESPACE
    True
    """

    items: tuple[Node, ...]
    wrapped: bool = True
    namespace: str | None = LVDATA_NAMESPACE

    def __post_init__(self) -> None:
        check_document(self)

    @property
    def version(self) -> str | None:
        """The text of the first ``<Version>`` header, if there is one."""
        for node in self.items:
            if node.tag == "Version":
                return node.val
        return None

    @property
    def values(self) -> tuple[Node, ...]:
        """The value nodes, leaving out ``Version`` headers."""
        return tuple(node for node in self.items if node.tag != "Version")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready dict that `Document.from_dict` turns back into this one."""
        from ._treejson import document_to_dict

        return document_to_dict(self)

    @staticmethod
    def from_dict(data: object) -> Document:
        """Build a document from the dict shape `to_dict` produces, checking every field."""
        from ._treejson import document_from_dict

        return document_from_dict(data)


Node.__module__ = Document.__module__ = "lvxml"

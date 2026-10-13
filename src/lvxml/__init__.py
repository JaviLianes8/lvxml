"""Codec between LabVIEW's Flatten/Unflatten XML schema and native Python values."""

from __future__ import annotations

from ._checks import validate
from ._decode import from_lv_xml, from_lv_xml_all, to_value
from ._dump import dump
from ._encode import to_lv_xml, to_node
from ._errors import LVXMLError
from ._node import LVDATA_NAMESPACE, Document, Node
from ._parse import parse
from ._schema import Array, Cluster, LVEnum

__version__ = "0.2.1"

__all__ = [
    "LVDATA_NAMESPACE",
    "Array",
    "Cluster",
    "Document",
    "LVEnum",
    "LVXMLError",
    "Node",
    "dump",
    "from_lv_xml",
    "from_lv_xml_all",
    "parse",
    "to_lv_xml",
    "to_node",
    "to_value",
    "validate",
]

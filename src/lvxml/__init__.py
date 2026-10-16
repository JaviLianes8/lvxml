"""Codec between LabVIEW's Flatten/Unflatten XML schema and native Python values.

`lvxml.LVDATA_NAMESPACE` is the namespace LabVIEW's XML file writer puts on ``<LVData>``.
`lvxml.Schema` is the type of a schema (a scalar tag string, `Array`, `Cluster` or `LVEnum`)
and `lvxml.Value` the type of a Python value this codec reads and writes, for annotations.

>>> import lvxml
>>> lvxml.from_lv_xml("<DBL><Name>x</Name><Val>0.25</Val></DBL>")
0.25
>>> lvxml.LVDATA_NAMESPACE
'http://www.ni.com/LVData'
>>> schema: lvxml.Schema = lvxml.Array("DBL")
>>> value: lvxml.Value = lvxml.from_lv_xml(lvxml.to_lv_xml([0.5], schema))
>>> value
[0.5]
"""

from __future__ import annotations

from ._checks import validate
from ._decode import from_lv_xml, from_lv_xml_all, to_value
from ._dump import dump
from ._encode import to_lv_xml, to_node
from ._errors import LVXMLError
from ._node import LVDATA_NAMESPACE, Document, Node
from ._parse import parse
from ._schema import Array, Cluster, LVEnum, Schema, Value

__version__ = "1.0.0"

__all__ = [
    "LVDATA_NAMESPACE",
    "Array",
    "Cluster",
    "Document",
    "LVEnum",
    "LVXMLError",
    "Node",
    "Schema",
    "Value",
    "dump",
    "from_lv_xml",
    "from_lv_xml_all",
    "parse",
    "to_lv_xml",
    "to_node",
    "to_value",
    "validate",
]

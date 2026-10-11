"""Codec between LabVIEW's Flatten/Unflatten XML schema and native Python values."""

from __future__ import annotations

from ._decode import from_lv_xml
from ._encode import to_lv_xml
from ._errors import LVXMLError
from ._schema import Array, Cluster

__version__ = "0.1.0"

__all__ = ["Array", "Cluster", "LVXMLError", "from_lv_xml", "to_lv_xml"]

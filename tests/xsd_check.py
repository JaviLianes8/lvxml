"""Validate LabVIEW XML against the official LVXMLSchema.xsd with lxml, when it is present."""

from __future__ import annotations

import pytest
from conftest import XSD
from lxml import etree

LVDATA_NS = "http://www.ni.com/LVData"
# The shipped XSD declares this target namespace, while LabVIEW's file writer puts
# LVDATA_NS on <LVData>. Validation maps one onto the other.
XSD_NS = "http://www.ni.com/labview"

# The schema is NI's and stays on the maintainer's machine; without it these tests skip.
requires_xsd = pytest.mark.skipif(
    not XSD.is_file(), reason="LVXMLSchema.xsd absent: run scripts/capture_ni.py"
)
_SCHEMA = etree.XMLSchema(etree.parse(str(XSD))) if XSD.is_file() else None


def xsd_valid(text: str) -> bool:
    """True if `text`, bare or wrapped, is valid against the XSD once namespaces are mapped."""
    if text.startswith("<?xml"):
        text = text.split("?>", 1)[1]
    if "<LVData" not in text:
        text = f'<LVData xmlns="{XSD_NS}">{text}</LVData>'
    text = text.replace(LVDATA_NS, XSD_NS)
    try:
        root = etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError:
        return False
    assert _SCHEMA is not None
    return bool(_SCHEMA.validate(root))


def xsd_valid_raw(text: str) -> bool:
    """True if `text` is valid against the XSD exactly as written, with no mapping."""
    if text.startswith("<?xml"):
        text = text.split("?>", 1)[1]
    assert _SCHEMA is not None
    return bool(_SCHEMA.validate(etree.fromstring(text.encode("utf-8"))))

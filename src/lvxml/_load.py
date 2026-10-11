"""Turn text or bytes into an XML element tree, keeping what a plain parse would lose."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ._errors import LVXMLError

_MARKUP = re.compile(r"(<[^>]*>)")
_DECLARATION = re.compile(r"\A﻿?\s*<\?xml\b[^>]*\?>")
_ENCODING = re.compile(rb"\A\s*<\?xml\b[^>]*\bencoding\s*=\s*[\"']([A-Za-z0-9._-]+)[\"']")


def decode(data: str | bytes) -> str:
    """Return `data` as text, decoding bytes by their XML declaration (default UTF-8)."""
    if isinstance(data, str):
        return data
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"expected str or bytes, got {type(data).__name__}")
    raw = bytes(data)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw, declared = raw[3:], "utf-8"
    else:
        match = _ENCODING.match(raw)
        declared = match.group(1).decode("ascii") if match else "utf-8"
    try:
        return raw.decode(declared)
    except (LookupError, UnicodeDecodeError) as exc:
        raise LVXMLError(f"cannot decode the input as {declared}: {exc}") from exc


def load(text: str) -> ET.Element:
    """Parse `text` into an element tree, refusing what LabVIEW XML never contains."""
    if "<!DOCTYPE" in text:
        raise LVXMLError("a DOCTYPE is not part of LabVIEW XML")
    if "<![CDATA[" in text:
        raise LVXMLError("CDATA sections are not supported; LabVIEW escapes text instead")
    # The text is already decoded, so an encoding named in the declaration must not apply.
    body = _DECLARATION.sub("", text, count=1)
    try:
        return ET.fromstring(_keep_carriage_returns(body))
    except ET.ParseError as exc:
        raise LVXMLError(f"invalid XML: {exc}") from exc


def _keep_carriage_returns(text: str) -> str:
    """Encode CRs inside the root element so the parser does not fold them into LFs."""
    if "\r" not in text:
        return text
    parts = _MARKUP.split(text)
    tags = [i for i in range(1, len(parts), 2) if not parts[i].startswith(("<?", "<!"))]
    if not tags:
        return text
    first, last = tags[0], tags[-1]
    return "".join(
        part.replace("\r", "&#13;") if first < i < last and i % 2 == 0 else part
        for i, part in enumerate(parts)
    )

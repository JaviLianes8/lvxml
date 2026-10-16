"""Turn text or bytes into an XML element tree, reading text the way LabVIEW reads it."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ._errors import LVXMLError
from ._text import quote

_MARKUP = re.compile(r"(<[^>]*>)")
_DECLARATION = re.compile(r"\A\ufeff?\s*<\?xml\b[^>]*\?>")
_ENCODING = re.compile(rb"\A\s*<\?xml\b[^>]*\bencoding\s*=\s*[\"']([A-Za-z0-9._-]+)[\"']")
# LabVIEW decodes only these three entities; any other ampersand is literal text to it.
_FOREIGN_AMPERSAND = re.compile(r"&(?!(?:lt|gt|amp);)")
# LabVIEW writes control characters raw although XML 1.0 forbids them. They travel through
# the parser as a private-use escape character followed by a private-use code.
_ESCAPE = "\ue000"
_HIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\ue020]")
_SHOWN = re.compile("\ue000([\ue001-\ue041])")


def decode(data: str | bytes | bytearray | memoryview) -> str:
    """Return `data` as text, decoding bytes by their XML declaration (default UTF-8).

    >>> decode(b"<?xml version='1.0' encoding='cp1252'?><a>\\xe9</a>")[-6:]
    '>é</a>'
    """
    if isinstance(data, str):
        return data
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"expected str or bytes, got {type(data).__name__}")
    raw = bytes(data)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw, declared = raw[3:], "utf-8"
    else:
        match = _ENCODING.match(raw)
        declared = match.group(1).decode("ascii") if match else "utf-8"
    try:
        return raw.decode(declared)
    except LookupError:
        raise LVXMLError(f"unknown encoding {quote(declared)} in the XML declaration") from None
    except UnicodeDecodeError as exc:
        hint = (
            "; LabVIEW writes files in the system code page, so decode them with it "
            "(for example cp1252) and pass the text"
            if declared == "utf-8"
            else ""
        )
        raise LVXMLError(f"cannot decode byte {exc.start} as {declared}{hint}") from None


def load(text: str) -> ET.Element:
    """Parse `text` into an element tree, refusing what LabVIEW XML never contains."""
    if "<!DOCTYPE" in text:
        raise LVXMLError("a DOCTYPE is not part of LabVIEW XML")
    if "<![CDATA[" in text:
        raise LVXMLError("CDATA sections are not supported; LabVIEW escapes text instead")
    # The text is already decoded, so an encoding named in the declaration must not apply.
    body = _DECLARATION.sub("", text, count=1)
    body = _hide(_FOREIGN_AMPERSAND.sub("&amp;", body))
    try:
        root = ET.fromstring(_keep_carriage_returns(body))
    except ET.ParseError as exc:
        raise LVXMLError(f"invalid XML: {exc}") from None
    if _ESCAPE in body:
        for element in root.iter():
            element.text = _show(element.text)
            element.tail = _show(element.tail)
    return root


def _hide(text: str) -> str:
    return _HIDDEN.sub(lambda m: _ESCAPE + chr(0xE001 + _offset(ord(m.group()))), text)


def _offset(code: int) -> int:
    return code if code < 0x20 else 0x20 + code - 0xE000


def _show(text: str | None) -> str | None:
    if text is None or _ESCAPE not in text:
        return text
    return _SHOWN.sub(lambda m: _code(ord(m.group(1)) - 0xE001), text)


def _code(offset: int) -> str:
    return chr(offset) if offset < 0x20 else chr(0xE000 + offset - 0x20)


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

"""The single error type raised for malformed or unsupported LabVIEW XML."""

from __future__ import annotations

# The longest message and location an error shows; longer ones keep their start and end.
_SHOWN = 200


class LVXMLError(ValueError):
    """Raised when LabVIEW XML or a tree is malformed or outside what LabVIEW writes.

    `message` says what is wrong and `path` where, for example
    ``LVData/Cluster[pt]/DBL[x]``; `path` is empty when there is no single location.
    Values quoted in a message are cut to 40 characters and ``str()`` of the error to
    a few hundred, so hostile input never produces a huge message.

    >>> from lvxml import from_lv_xml
    >>> try:
    ...     from_lv_xml("<I8><Name>n</Name><Val>300</Val></I8>")
    ... except LVXMLError as error:
    ...     print(error.path, "|", error.message)
    I8[n] | 300 is out of range for I8 (-128..127)
    """

    def __init__(self, message: str, path: str = "") -> None:
        shown = f"{cut(path)}: {cut(message)}" if path else cut(message)
        super().__init__(shown)
        self.message = cut(message)
        self.path = path

    def __reduce__(self) -> tuple[type[LVXMLError], tuple[str, str]]:
        return type(self), (self.message, self.path)


def cut(text: str) -> str:
    """Return `text`, or its start and end around ``...`` when it is too long to show."""
    if len(text) <= _SHOWN:
        return text
    half = (_SHOWN - 5) // 2
    return f"{text[:half]} ... {text[-half:]}"


LVXMLError.__module__ = "lvxml"

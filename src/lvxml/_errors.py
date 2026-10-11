"""The single error type raised for malformed or unsupported LabVIEW XML."""

from __future__ import annotations


class LVXMLError(ValueError):
    """Raised when LabVIEW XML is malformed or falls outside the covered subset.

    `path` locates the offending element, for example ``LVData/Cluster[pt]/DBL[x]``, and
    is empty when the problem has no single location.
    """

    def __init__(self, message: str, path: str = "") -> None:
        super().__init__(f"{path}: {message}" if path else message)
        self.message = message
        self.path = path

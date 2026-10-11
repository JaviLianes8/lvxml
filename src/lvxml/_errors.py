"""The single error type raised for malformed or unsupported LabVIEW XML."""

from __future__ import annotations


class LVXMLError(ValueError):
    """Raised when LabVIEW XML is malformed or falls outside the covered subset."""

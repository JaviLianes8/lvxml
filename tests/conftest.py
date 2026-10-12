"""Shared paths to the ground-truth fixtures."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
# NI's schema is not tracked: scripts/capture_ni.py copies it from a LabVIEW install.
XSD = FIXTURES / "ni" / "LVXMLSchema.xsd"
# Written by LabVIEW 2026 itself (see README, "Test fixtures").
REAL_FILES = sorted((FIXTURES / "real").glob("*.xml"))
# Hand-written from LVXMLSchema.xsd to cover every element it defines.
SCHEMA_FILES = sorted((FIXTURES / "schema").glob("*.xml"))


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")

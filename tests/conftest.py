"""Shared paths to the ground-truth fixtures."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
XSD = FIXTURES / "LVXMLSchema.xsd"
# Written by LabVIEW 2026 itself (see README, "Test fixtures").
REAL_FILES = sorted((FIXTURES / "real").glob("*.xml"))
# Hand-written from LVXMLSchema.xsd to cover every element it defines.
SCHEMA_FILES = sorted((FIXTURES / "schema").glob("*.xml"))


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")

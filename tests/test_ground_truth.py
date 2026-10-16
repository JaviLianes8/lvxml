"""The complete promise, checked against LabVIEW's own XSD and a file LabVIEW wrote."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from conftest import FIXTURES, REAL_FILES, SCHEMA_FILES, XSD, read
from xsd_check import requires_xsd, xsd_valid, xsd_valid_raw

import lvxml
from lvxml._schema import VALUE_TAGS, Value

ALL_FILES = REAL_FILES + SCHEMA_FILES


def _canonical(text: str) -> str:
    if text.startswith("<?xml"):
        text = text.split("?>", 1)[1]
    return ET.canonicalize(text.strip(), strip_text=True)


def test_there_is_at_least_one_real_labview_file() -> None:
    assert REAL_FILES, "tests/fixtures/real must hold LabVIEW-written XML"


def test_the_real_file_carries_labview_headers() -> None:
    raw = REAL_FILES[0].read_bytes()
    assert raw.startswith(b"<?xml version='1.0' standalone='yes' ?>\r\n<LVData")
    assert lvxml.parse(raw.decode("utf-8")).version == "26.3.1f1"


@requires_xsd
def test_the_codec_knows_exactly_the_value_elements_the_xsd_defines() -> None:
    schema = ET.parse(XSD).getroot()
    xs = "{http://www.w3.org/2001/XMLSchema}"
    root_type = next(
        t for t in schema.iter(f"{xs}complexType") if t.get("name") == "LVDataRootType"
    )
    declared = {el.get("name") for el in root_type.iter(f"{xs}element")} - {"Version"}
    assert declared == set(VALUE_TAGS)


@requires_xsd
@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_fixture_is_valid_against_the_xsd(path: Path) -> None:
    assert xsd_valid(read(path))


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_fixture_passes_validate(path: Path) -> None:
    assert lvxml.validate(read(path)) == []


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_value_decodes(path: Path) -> None:
    document = lvxml.parse(read(path))
    values = lvxml.from_lv_xml_all(read(path))
    assert len(values) == len(document.values) > 0


@pytest.mark.parametrize("path", REAL_FILES, ids=lambda p: p.name)
def test_a_labview_written_file_round_trips_byte_for_byte(path: Path) -> None:
    raw = read(path)
    assert lvxml.dump(lvxml.parse(raw)).encode("utf-8") == path.read_bytes()


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_fixture_round_trips_canonically(path: Path) -> None:
    raw = read(path)
    written = lvxml.dump(lvxml.parse(raw))
    assert lvxml.parse(written) == lvxml.parse(raw)
    if "<RefKind>" not in raw:  # dump moves RefKind before <Val>, where LabVIEW writes it
        assert _canonical(written) == _canonical(raw)


@requires_xsd
@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_every_rewritten_fixture_is_valid_against_the_xsd(path: Path) -> None:
    written = lvxml.dump(lvxml.parse(read(path)))
    assert xsd_valid(written) == ("<RefKind>" not in written)


@requires_xsd
def test_labview_writes_refkind_before_val_against_its_own_xsd() -> None:
    raw = (FIXTURES / "labview2026" / "save-cont-paths.xml").read_bytes().decode("cp1252")
    kind = "<RefKind>TDMS File</RefKind>\r\n"
    assert kind + "<Val>0x00000000</Val>" in raw
    assert not xsd_valid(raw)
    assert xsd_valid(raw.replace(kind, ""))


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_the_tree_survives_json(path: Path) -> None:
    document = lvxml.parse(read(path))
    data = json.loads(json.dumps(document.to_dict()))
    assert lvxml.Document.from_dict(data) == document


def test_real_file_values() -> None:
    values = lvxml.from_lv_xml_all(read(REAL_FILES[0]))
    assert values[:3] == [0.99191378202678, 0.11250854849828, 0.5286296086762]
    graph = values[3]
    assert isinstance(graph, dict)
    assert list(graph) == ["Initial X", "Delta X", "Values"]
    assert graph["Delta X"] == 0.25
    samples = graph["Values"]
    assert isinstance(samples, list)
    assert len(samples) == 10
    assert min(samples) == values[1]  # type: ignore[type-var]
    assert max(samples) == values[0]  # type: ignore[type-var]


@requires_xsd
def test_real_file_needs_the_namespace_mapping_to_meet_the_xsd() -> None:
    # LabVIEW writes xmlns="http://www.ni.com/LVData"; the XSD targets another namespace.
    assert not xsd_valid_raw(read(REAL_FILES[0]))


@requires_xsd
def test_encoded_values_are_valid_against_the_xsd() -> None:
    schema = lvxml.Cluster(
        {
            "n": "I64",
            "x": "EXT",
            "z": "CXT",
            "on": "Boolean",
            "p": "Path",
            "s": "String",
            "ch": "DAQChannel",
            "mode": lvxml.LVEnum(("a", "b"), "EB"),
            "grid": lvxml.Array("SGL", 2),
            "none": lvxml.Array(lvxml.Cluster({"u": "U16"})),
        }
    )
    value: Value = {
        "n": -1,
        "x": 0.5,
        "z": 1 - 1j,
        "on": False,
        "p": "C:\\x",
        "s": "<&>",
        "ch": "Dev1/ai0",
        "mode": "b",
        "grid": [[1.0, 2.0], [3.0, 4.0]],
        "none": [],
    }
    node = lvxml.to_node(value, schema, "all")
    assert xsd_valid(lvxml.dump(node))
    assert xsd_valid(lvxml.to_lv_xml(value, schema, "all"))
    assert lvxml.to_value(node) == value

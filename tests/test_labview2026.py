"""Ground truth from LabVIEW 2026 itself (see scripts/capture-labview-xml.ps1).

`save-*.xml` are files LabVIEW wrote from values this suite chose (`jobs.json`); the
`load-*.json` files hold what LabVIEW read from each hand-written or lvxml-written input in
`inputs/`. Every check compares lvxml with LabVIEW, never with lvxml's own output.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from conftest import FIXTURES

from lvxml import LVXMLError, dump, from_lv_xml, parse, to_value

HERE = FIXTURES / "labview2026"
JOBS: list[dict[str, Any]] = json.loads((HERE / "jobs.json").read_text(encoding="utf-8"))
SAVES = [job for job in JOBS if job["kind"] == "save"]
SINGLE = [job for job in JOBS if job["kind"] == "load" and "single" in job["name"]]
DOUBLE = [job for job in JOBS if job["kind"] == "load" and "dbl" in job["name"]]
# The shipped settings VI falls back to these values whenever LabVIEW refuses the file.
REFUSED = [["", 0], [True], 0]
# Inputs LabVIEW's file reader refuses for its own reasons while lvxml reads them: the bare
# Flatten To XML form and an <LVData> file without a <Version> header.
FILE_READER_ONLY = {
    "load-single-bare",
    "load-single-no-version",
    "load-single-lvxml-dump",
    "load-single-lvxml-to-lv-xml",
}


def plain(node: dict[str, Any]) -> Any:
    return [plain(item) for item in node["v"]] if node["t"] == "cluster" else node["v"]


def text_of(path: Path) -> str:
    return path.read_bytes().decode("cp1252")


@pytest.mark.parametrize("job", SAVES, ids=[job["name"] for job in SAVES])
def test_files_labview_wrote_come_back_byte_for_byte(job: dict[str, Any]) -> None:
    text = text_of(HERE / job["out"])
    document = parse(text)
    assert document.version == "26.3.1f1"
    assert dump(document) == text


@pytest.mark.parametrize("job", SAVES, ids=[job["name"] for job in SAVES])
def test_values_read_are_the_values_labview_was_given(job: dict[str, Any]) -> None:
    (node,) = parse(text_of(HERE / job["out"])).values
    value: Any = to_value(node)
    assert isinstance(value, dict)
    given = plain(job["value"])
    hardware = list(value["Hardware Configuration"].values())
    signal = node.items[0].items[1]
    assert hardware[0] == given[0][0]
    assert signal.choices.index(hardware[1]) == given[0][1]
    if "cont" in job["name"]:
        logging = value["Logging Configuration"]
        assert logging["Log File Base Path"] == given[1][0]
        assert logging["TDMS File Reference"] == "0x00000000"
        assert node.items[1].items[1].extra == (("RefKind", "TDMS File"),)
    else:
        assert value["Analysis Configuration"] == {"Statistics": given[1][0]}
        behaviour = node.items[2]
        assert behaviour.choices.index(value["New Data Behavior"]) == given[2]


def test_labview_writes_the_system_code_page_not_utf8() -> None:
    raw = (HERE / "save-cont-codepage.xml").read_bytes()
    assert b"caf\xe9 \x805" in raw and b"encoding" not in raw
    with pytest.raises(LVXMLError, match="system code page"):
        parse(raw)
    assert "caf\u00e9 \u20ac5" in str(from_lv_xml(raw.decode("cp1252")))


def test_labview_writes_control_characters_raw_and_lvxml_reads_them() -> None:
    raw = (HERE / "save-cont-control.xml").read_bytes()
    assert b"bell\x07 unit\x1f" in raw
    value: Any = from_lv_xml(raw)
    assert isinstance(value, dict)
    assert value["Hardware Configuration"]["HW Refnum <Replace Me>"] == "bell\x07 unit\x1f"


def test_labview_escapes_only_ampersand_and_angle_brackets() -> None:
    raw = (HERE / "save-cont-escapes.xml").read_bytes()
    assert b"a&amp;b&lt;c&gt;d \"q\" 'p' ]]&gt; tab\tend cr\rlf\ncrlf\r\nx " in raw


def loaded(job: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((HERE / job["out"]).read_text(encoding="utf-8"))
    return result


def expected_single(result: dict[str, Any]) -> dict[str, Any]:
    (text, signal), (stats,), behaviour = result["User Configuration out"]
    return {"text": text, "signal": signal, "stats": stats, "behaviour": behaviour}


def lvxml_single(text: str) -> dict[str, Any]:
    value: Any = from_lv_xml(text)
    assert isinstance(value, dict)
    (node,) = parse(text).values
    hardware, analysis = value["Hardware Configuration"], value["Analysis Configuration"]
    signal_node, behaviour_node = node.items[0].items[1], node.items[2]
    return {
        "text": hardware["HW Refnum <Replace Me>"],
        "signal": signal_node.choices.index(hardware["Signal Type <Replace Me>"]),
        "stats": analysis["Statistics"],
        "behaviour": behaviour_node.choices.index(value["New Data Behavior"]),
    }


@pytest.mark.parametrize("job", SINGLE, ids=[job["name"] for job in SINGLE])
def test_lvxml_reads_what_labview_reads_and_refuses_what_it_refuses(job: dict[str, Any]) -> None:
    result = loaded(job)
    assert result["finished"] and result["error out"] == [False, 0, ""]
    text = text_of(HERE / job["input"])
    accepted = result["User Configuration out"] != REFUSED
    if job["name"] == "load-single-enum-past":
        # LabVIEW clamps an index past the last choice; lvxml reports the inconsistency.
        assert expected_single(result)["behaviour"] == 2
        with pytest.raises(LVXMLError, match="past its 3 choices"):
            from_lv_xml(text)
    elif accepted:
        assert lvxml_single(text) == expected_single(result)
    elif job["name"] in FILE_READER_ONLY:
        lvxml_single(text)
    else:
        with pytest.raises(LVXMLError):
            from_lv_xml(text)


def test_labview_reads_what_lvxml_writes_into_a_file_with_a_version() -> None:
    result = expected_single(loaded({"out": "load-single-lvxml-dump-version.json"}))
    assert result == {"text": 'a&b <"q">', "signal": 1, "stats": False, "behaviour": 2}


def labview_number(found: object) -> float:
    names = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}
    return names[found] if isinstance(found, str) else float(found)  # type: ignore[arg-type]


@pytest.mark.parametrize("job", DOUBLE, ids=[job["name"] for job in DOUBLE])
def test_lvxml_reads_doubles_as_labview_does(job: dict[str, Any]) -> None:
    result = loaded(job)
    nodes = parse(text_of(HERE / job["input"])).values[:3]
    for node, key in zip(nodes, ("Max", "Min", "Mean"), strict=True):
        found = labview_number(result[key])
        # LabVIEW leaves 0 behind for a value it refuses and then reports the error.
        if not result["finished"] and found == 0.0:
            with pytest.raises(LVXMLError):
                to_value(node)
            continue
        value = to_value(node)
        assert isinstance(value, float)
        assert (math.isnan(value) and math.isnan(found)) or value == found, node.val
        assert math.copysign(1.0, value) == math.copysign(1.0, found)

"""Contracts added for the mutants that survived the author's mutation round."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lvxml import LVXMLError, parse, to_lv_xml
from lvxml._cli import main
from lvxml._parse import MAX_DEPTH


def nested(levels: int) -> str:
    opening = "<Cluster><Name>c</Name><NumElts>1</NumElts>" * (levels - 1)
    return opening + "<I8><Name>n</Name><Val>1</Val></I8>" + "</Cluster>" * (levels - 1)


def test_nesting_is_allowed_up_to_max_depth_and_refused_one_deeper() -> None:
    assert MAX_DEPTH == 100
    assert parse(nested(MAX_DEPTH)).values
    with pytest.raises(LVXMLError, match="deeper than 100"):
        parse(nested(MAX_DEPTH + 1))


@pytest.mark.parametrize("tag", ["I8", "U64", "DBL", "CDB"])
def test_a_bool_is_not_a_number(tag: str) -> None:
    with pytest.raises(LVXMLError, match="expects"):
        to_lv_xml(True, tag)


def test_an_error_built_from_huge_text_stays_short() -> None:
    error = LVXMLError("m" * 5000, "p" * 5000)
    assert len(str(error)) <= 410
    assert len(error.message) <= 200
    assert str(error).startswith("p" * 97) and str(error).endswith("m" * 97)


def test_every_command_line_is_bounded(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "x" * 1000 + ".xml"]) == 1
    lines = capsys.readouterr().err.splitlines()
    assert lines and all(len(line) <= 300 for line in lines)


def test_to_xml_reads_its_json_as_utf8_whatever_the_xml_encoding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = tmp_path / "t.json"
    node = {"tag": "String", "name": "s", "val": "café"}
    tree.write_bytes(json.dumps({"wrapped": False, "items": [node]}, ensure_ascii=False).encode())
    out = tmp_path / "t.xml"
    assert main(["to-xml", "--encoding", "cp1252", str(tree), "-o", str(out)]) == 0
    assert b"<Val>caf\xe9</Val>" in out.read_bytes()

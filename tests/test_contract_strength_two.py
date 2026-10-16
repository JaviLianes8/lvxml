"""Contracts from the blind mutation round of the contract-strength lens: values, trees, CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from lvxml import Array, Document, LVEnum, LVXMLError, Node, dump, from_lv_xml, parse, to_node
from lvxml._cli import main

SRC = Path(__file__).resolve().parents[1] / "src"


def fails(call: Callable[[], object]) -> LVXMLError:
    with pytest.raises(LVXMLError) as info:
        call()
    return info.value


def test_from_lv_xml_returns_the_first_value() -> None:
    xml = (
        "<LVData><Version>1</Version><I8><Name>a</Name><Val>1</Val></I8>"
        "<I8><Name>b</Name><Val>2</Val></I8></LVData>"
    )
    assert from_lv_xml(xml) == 1


def test_an_empty_container_is_an_empty_list() -> None:
    assert from_lv_xml("<LvVariant><Name>v</Name></LvVariant>") == []
    assert from_lv_xml("<Timestamp><Name>t</Name></Timestamp>") == []


def test_an_lvdata_without_values_raises_lvxml_error() -> None:
    fails(lambda: from_lv_xml("<LVData><Version>1</Version></LVData>"))


def test_a_negative_enum_index_is_refused() -> None:
    fails(lambda: to_node(-1, LVEnum(("a", "b"))))


def test_an_empty_enum_array_carries_the_first_choice() -> None:
    assert to_node([], Array(LVEnum(("a", "b")))).items[0].val == "0"


def test_an_unnamed_value_is_located_as_value() -> None:
    assert fails(lambda: to_node("x", "DBL")).path == "value"


def test_an_empty_array_has_one_size_per_dimension() -> None:
    assert to_node([], Array("I8", ndim=2)).dims == (0, 0)
    assert to_node([], Array("I8", ndim=3)).dims == (0, 0, 0)


def test_a_quote_in_the_namespace_is_escaped_and_survives() -> None:
    document = Document((Node("Version", val="1"),), namespace='a"b&c')
    assert '<LVData xmlns="a&quot;b&amp;c">' in dump(document)
    assert parse(dump(document)) == document


def test_a_version_node_only_takes_a_val() -> None:
    fails(lambda: dump(Document((Node("Version", "x", val="1"),))))


def test_refnum_group_fields_are_indented_one_level_deeper() -> None:
    extra = (("ActiveXType.GUID", "g"), ("ActiveXType.Name", "n"))
    node = Node("Refnum", "r", val="0x1", extra=extra)
    assert dump(node, newline="\n", indent="  ").splitlines()[3:7] == [
        "  <ActiveXType>",
        "    <GUID>g</GUID>",
        "    <Name>n</Name>",
        "  </ActiveXType>",
    ]


@pytest.mark.parametrize("code", [0xFFFE, 0xFFFF])
def test_noncharacters_cannot_be_written(code: int) -> None:
    fails(lambda: dump(Node("String", "s", val=chr(code))))


def test_a_bare_document_holds_exactly_one_value() -> None:
    two = (Node("I8", "a", val="1"), Node("I8", "b", val="2"))
    fails(lambda: dump(Document(two, wrapped=False, namespace=None)))


def test_negative_dimsize_is_refused_by_dump_and_from_dict() -> None:
    fails(lambda: dump(Node("Array", "a", dims=(-1,), items=(Node("I8", val="0"),))))
    fails(lambda: Node.from_dict({"tag": "Array", "name": "", "dims": [-1], "items": []}))


def test_a_version_entry_has_no_name() -> None:
    items: Any = Document((Node("Version", val="1"),)).to_dict()["items"]
    assert items[0] == {"tag": "Version", "val": "1"}


def test_refnum_fields_must_keep_their_order() -> None:
    node = Node("Refnum", "r", val="0x1", extra=(("RefType", "t"), ("RefKind", "k")))
    fails(lambda: dump(node))


def nested(depth: int) -> dict[str, object]:
    data: dict[str, object] = {"tag": "I8", "name": "", "val": "1"}
    for _ in range(depth - 1):
        data = {"tag": "LvVariant", "name": "", "items": [data]}
    return data


def test_the_from_dict_depth_limit() -> None:
    assert Node.from_dict(nested(100)).tag == "LvVariant"
    fails(lambda: Node.from_dict(nested(101)))


def test_empty_containers_keep_an_items_list() -> None:
    cluster = {"tag": "Cluster", "name": "c", "num_elts": 0, "items": []}
    assert Node("Cluster", "c", num_elts=0).to_dict() == cluster
    assert Node("LvVariant", "v").to_dict() == {"tag": "LvVariant", "name": "v", "items": []}


def test_to_json_values_reports_the_lvdata_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "a.xml"
    path.write_text(
        "<LVData><Version>1</Version><I8><Name>n</Name><Val>300</Val></I8></LVData>",
        encoding="utf-8",
    )
    assert main(["to-json", "--values", str(path)]) == 1
    assert "LVData/I8[n]" in capsys.readouterr().err


def test_validate_goes_on_after_a_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = tmp_path / "good.xml"
    good.write_text("<I8><Name>n</Name><Val>1</Val></I8>", encoding="utf-8")
    assert main(["validate", str(tmp_path / "missing.xml"), str(good)]) == 1
    assert f"{good}: OK" in capsys.readouterr().out


def test_no_standard_input_is_a_clean_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    assert main(["to-json", "-"]) == 1
    assert "no standard input" in capsys.readouterr().err


def test_python_m_lvxml_returns_the_exit_status(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run(
        [sys.executable, "-m", "lvxml", "validate", str(tmp_path / "missing.xml")],
        capture_output=True,
        env=env,
        check=False,
        timeout=120,
    )
    assert result.returncode == 1

"""Contracts added for the findings of the adversarial lens: hostile input stays cheap and safe."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from lvxml import LVXMLError, Node, dump, from_lv_xml, from_lv_xml_all, parse, to_value, validate
from lvxml._cli import main

DBL = "<DBL><Name>n</Name><Val>{}</Val></DBL>"
CDB = "<CDB><Name>n</Name><Val>{}</Val></CDB>"


@pytest.mark.parametrize(
    "text",
    [
        DBL.format("1" * 999 + "x"),
        CDB.format("1 +" + "1" * 990 + "x i"),
        CDB.format("+" * 999),
        DBL.format("1" * 5000),
        "<I8><Name>n</Name><Val>" + "9" * 5000 + "</Val></I8>",
        "<Boolean><Name>n</Name><Val>" + "1" * 5000 + "</Val></Boolean>",
    ],
    ids=["float", "complex", "pluses", "long float", "long int", "long bool"],
)
def test_hostile_numbers_are_refused_quickly(text: str) -> None:
    started = time.perf_counter()
    assert validate(text)
    with pytest.raises(LVXMLError):
        from_lv_xml(text)
    assert time.perf_counter() - started < 0.5


@pytest.mark.parametrize(
    "text",
    [
        "<Array><Name>a</Name><Dimsize>" + "1" * 5000 + "</Dimsize></Array>",
        "<Cluster><Name>c</Name><NumElts>9223372036854775808</NumElts></Cluster>",
        "<Array><Name>a</Name>" + "<Dimsize>1</Dimsize>" * 101 + "</Array>",
        "<Array><Name>a</Name>"
        + "<Dimsize>1</Dimsize>" * 3000
        + "<I8><Name></Name><Val>1</Val></I8></Array>",
    ],
    ids=["long dimsize", "numelts past 2**63", "101 dims", "3000 dims"],
)
def test_huge_counts_and_too_many_dimensions_are_refused(text: str) -> None:
    for call in (parse, from_lv_xml, from_lv_xml_all):
        with pytest.raises(LVXMLError):
            call(text)
    assert len(validate(text)) == 1


def test_a_huge_product_of_sizes_is_reported_quickly_and_briefly() -> None:
    text = "<Array><Name>a</Name>" + "<Dimsize>9223372036854775807</Dimsize>" * 100 + "</Array>"
    started = time.perf_counter()
    problems = validate(text)
    assert time.perf_counter() - started < 0.5
    assert problems and all(len(problem) <= 400 for problem in problems)


@pytest.mark.parametrize(
    "field", [{"num_elts": 10**5000}, {"dims": (10**5000,)}], ids=["num_elts", "dims"]
)
def test_trees_with_huge_counts_are_refused(field: dict[str, object]) -> None:
    tag = "Cluster" if "num_elts" in field else "Array"
    node = Node(tag, "c", **field)  # type: ignore[arg-type]
    for call in (dump, to_value):
        with pytest.raises(LVXMLError, match="larger than"):
            call(node)


def test_text_python_cannot_carry_is_an_lvxml_error() -> None:
    with pytest.raises(LVXMLError, match="surrogate"):
        parse("<String><Name>s</Name><Val>\ud800</Val></String>")
    with pytest.raises(LVXMLError, match="cannot decode"):
        parse(b"<?xml version='1.0' encoding='undefined'?><I8/>")


def test_a_namespace_with_private_use_characters_survives() -> None:
    text = '<DBL xmlns="u\x01"><Name>x</Name><Val>1</Val></DBL>'
    document = parse(text)
    assert document.namespace == "u\x01"
    assert parse(dump(document)) == document


def test_mixed_key_types_in_a_tree_dict_are_an_lvxml_error() -> None:
    with pytest.raises(LVXMLError, match="unknown node fields"):
        Node.from_dict({"tag": "DBL", "name": "", "val": "1", 1: 2, "x": 3})


@pytest.mark.parametrize("encoding", ["base64", "rot13", "hex", "zlib", "undefined"])
def test_codecs_that_are_not_text_encodings_are_usage_mistakes(
    encoding: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = tmp_path / "g.xml"
    good.write_text(DBL.format("1"), encoding="utf-8")
    assert main(["validate", "--encoding", encoding, str(good)]) == 2
    assert "unknown text encoding" in capsys.readouterr().err


def test_a_huge_json_integer_is_a_problem_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = tmp_path / "t.json"
    tree.write_text('{"items": [' + "1" * 5000 + "]}", encoding="utf-8")
    assert main(["to-xml", str(tree)]) == 1
    assert "invalid JSON" in capsys.readouterr().err


def test_the_command_line_never_echoes_control_characters_or_line_breaks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hostile = tmp_path / "h.xml"
    name = "\x1b]0;pwned\x07\x1b[2J x\nfake.xml: OK\n"
    hostile.write_text(f"<I8><Name>{name}</Name><Val>300</Val></I8>", encoding="utf-8")
    assert main(["validate", str(hostile)]) == 1
    err = capsys.readouterr().err
    assert "\x1b" not in err and "\x07" not in err
    assert err.count("\n") == 1 and "fake.xml: OK" in err

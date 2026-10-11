"""Hostile or unusual input fails fast with an LVXMLError instead of misbehaving."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lvxml import (
    LVDATA_NAMESPACE,
    Document,
    LVEnum,
    LVXMLError,
    Node,
    dump,
    from_lv_xml,
    parse,
    to_node,
    to_value,
    validate,
)
from lvxml._cli import main


def _deep_clusters(depth: int) -> str:
    opened = "<Cluster><Name>c</Name><NumElts>1</NumElts>" * depth
    return opened + "<I8><Name>x</Name><Val>1</Val></I8>" + "</Cluster>" * depth


def test_huge_empty_shape_is_refused_quickly() -> None:
    text = "<Array><Name></Name><Dimsize>99999999999999999999</Dimsize><Dimsize>0</Dimsize></Array>"
    started = time.perf_counter()
    with pytest.raises(LVXMLError, match="needs over 100000 lists"):
        from_lv_xml(text)
    assert len(validate(text)) == 1
    assert time.perf_counter() - started < 5


def test_moderate_empty_shape_still_decodes() -> None:
    text = "<Array><Name></Name><Dimsize>1000</Dimsize><Dimsize>0</Dimsize></Array>"
    assert from_lv_xml(text) == [[] for _ in range(1000)]


def test_cdata_is_refused() -> None:
    with pytest.raises(LVXMLError, match="CDATA"):
        parse("<String><Name>s</Name><Val><![CDATA[a>\rb]]></Val></String>")


def test_children_must_share_the_root_namespace() -> None:
    text = (
        "<LVData xmlns='http://www.ni.com/LVData'><x:I32 xmlns:x='urn:other'>"
        "<x:Name>n</x:Name><x:Val>1</x:Val></x:I32></LVData>"
    )
    with pytest.raises(LVXMLError, match="namespace"):
        parse(text)


def test_deep_nesting_is_refused_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert from_lv_xml(_deep_clusters(50)) is not None
    with pytest.raises(LVXMLError, match="nesting deeper than 100"):
        parse(_deep_clusters(600))
    deep = tmp_path / "deep.xml"
    deep.write_text(_deep_clusters(600), encoding="utf-8")
    assert main(["validate", str(deep)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_deep_hand_built_tree_raises_lvxml_error() -> None:
    node = Node("I8", "x", val="1")
    for _ in range(5000):
        node = Node("Cluster", "c", num_elts=1, items=(node,))
    with pytest.raises(LVXMLError, match="nesting deeper than 100"):
        dump(node)
    with pytest.raises(LVXMLError, match="nesting deeper than 100"):
        to_value(node)


def test_unwritable_text_is_an_lvxml_error() -> None:
    with pytest.raises(LVXMLError, match="U\\+D800"):
        dump(Node("String", "s", val="\ud800"))


def test_cli_reports_unencodable_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tree = tmp_path / "t.json"
    tree.write_text(
        json.dumps({"wrapped": False, "items": [{"tag": "String", "name": "s", "val": "日"}]}),
        encoding="utf-8",
    )
    assert main(["to-xml", "--encoding", "cp1252", str(tree)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("lvxml: error:")
    assert "cp1252" in err


def test_values_json_is_strict(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "n.xml"
    source.write_text(
        "<Cluster><Name>c</Name><NumElts>2</NumElts><DBL><Name>a</Name><Val>NaN</Val></DBL>"
        "<CDB><Name>z</Name><Val>-Inf +1 i</Val></CDB></Cluster>",
        encoding="utf-8",
    )
    assert main(["to-json", "--values", str(source)]) == 0

    def refuse(name: str) -> object:
        raise AssertionError(f"non-standard JSON constant {name}")

    data = json.loads(capsys.readouterr().out, parse_constant=refuse)
    assert data[0]["value"] == {"a": "NaN", "z": {"re": "-Inf", "im": 1.0}}


def test_bytes_input_is_decoded_by_its_declaration() -> None:
    assert from_lv_xml(b"<I8><Name>n</Name><Val>1</Val></I8>") == 1
    latin = (
        "<?xml version='1.0' encoding='windows-1252'?>"
        "<String><Name>s</Name><Val>caf\xe9</Val></String>"
    )
    assert from_lv_xml(latin.encode("cp1252")) == "caf\xe9"
    assert from_lv_xml(latin) == "caf\xe9"  # already text: the declared encoding is not reapplied
    assert from_lv_xml(b"\xef\xbb\xbf<I8><Name>n</Name><Val>2</Val></I8>") == 2
    with pytest.raises(LVXMLError, match="cannot decode"):
        from_lv_xml(b"<I8><Name>\xff</Name><Val>1</Val></I8>")
    with pytest.raises(TypeError, match="str or bytes"):
        from_lv_xml(12)  # type: ignore[arg-type]


def test_enum_choices_are_normalized() -> None:
    enum = LVEnum(["a", "b"])  # type: ignore[arg-type]
    assert enum.choices == ("a", "b")
    assert hash(to_node("a", enum))
    with pytest.raises(TypeError):
        LVEnum("ab")  # type: ignore[arg-type]


def test_schema_of_the_wrong_type_is_a_clear_type_error() -> None:
    with pytest.raises(TypeError, match="a schema is a tag string"):
        to_node(1, ["DBL"])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "data",
    [
        {"items": [{"tag": "DBL", "val": "1"}]},
        {"items": [], "colour": "red"},
        {"items": [{"tag": "Cluster", "name": "c", "num_elts": -1, "items": []}]},
    ],
)
def test_from_dict_is_as_strict_as_parse(data: object) -> None:
    with pytest.raises(LVXMLError):
        Document.from_dict(data)


def test_from_dict_namespace_defaults_like_the_dataclass() -> None:
    assert Document.from_dict({"items": []}).namespace == LVDATA_NAMESPACE == Document(()).namespace


def test_empty_array_default_element_is_still_checked() -> None:
    text = "<Array><Name>a</Name><Dimsize>0</Dimsize><I32><Name/><Val>xx</Val></I32></Array>"
    with pytest.raises(LVXMLError, match="invalid integer"):
        from_lv_xml(text)


def test_to_value_refuses_tags_outside_the_schema() -> None:
    with pytest.raises(LVXMLError, match="unknown LabVIEW type tag"):
        to_value(Node("FXP", "f", val="1"))

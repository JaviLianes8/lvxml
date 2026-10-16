"""One promise test per public name, covering the 1.0.0 rules and their failure paths."""

from __future__ import annotations

import math
import pickle

import pytest

import lvxml
from lvxml import (
    LVDATA_NAMESPACE,
    Array,
    Cluster,
    Document,
    LVEnum,
    LVXMLError,
    Node,
    dump,
    from_lv_xml,
    from_lv_xml_all,
    parse,
    to_lv_xml,
    to_node,
    to_value,
    validate,
)


def string(val: str) -> str:
    return f"<String><Name>s</Name><Val>{val}</Val></String>"


def boolean(val: str) -> str:
    return f"<Boolean><Name>b</Name><Val>{val}</Val></Boolean>"


def test_lvdata_namespace_is_labviews() -> None:
    assert LVDATA_NAMESPACE == "http://www.ni.com/LVData"
    assert Document(()).namespace == LVDATA_NAMESPACE


@pytest.mark.parametrize(
    ("val", "text"),
    [
        ("&quot;&apos;&#13;&#x41;", "&quot;&apos;&#13;&#x41;"),
        ("a & b &c; &#;", "a & b &c; &#;"),
        ("&lt;&gt;&amp;", "<>&"),
        ("a\r\nb\rc", "a\r\nb\rc"),
        ("\x00\x01\x08\x0b\x0c\x0e\x1f", "\x00\x01\x08\x0b\x0c\x0e\x1f"),
        ("", ""),
    ],
)
def test_text_is_read_as_labview_reads_it(val: str, text: str) -> None:
    assert from_lv_xml(string(val)) == text
    (node,) = parse(string(val)).values
    assert parse(dump(node)).values[0] == node


@pytest.mark.parametrize(
    ("val", "value"), [("1", True), ("0", False), ("2", True), (" 1 ", True), ("00", False)]
)
def test_booleans_are_unsigned_digits(val: str, value: bool) -> None:
    assert from_lv_xml(boolean(val)) is value


@pytest.mark.parametrize("val", ["true", "TRUE", "false", "-1", "+1", "", "1.0", "\u0661"])
def test_other_boolean_text_is_refused(val: str) -> None:
    with pytest.raises(LVXMLError, match="invalid boolean"):
        from_lv_xml(boolean(val))


@pytest.mark.parametrize("val", ["Infinity", "-infinity", "+NaN", "-NaN", "1,5", "", "0x10", "1_0"])
def test_floats_labview_refuses_are_refused(val: str) -> None:
    with pytest.raises(LVXMLError, match="invalid float"):
        from_lv_xml(f"<DBL><Name>x</Name><Val>{val}</Val></DBL>")


@pytest.mark.parametrize(
    ("val", "value"),
    [
        ("+Inf", math.inf),
        ("inf", math.inf),
        ("-INF", -math.inf),
        (" .5 ", 0.5),
        ("1e400", math.inf),
    ],
)
def test_floats_labview_reads_are_read(val: str, value: float) -> None:
    assert from_lv_xml(f"<DBL><Name>x</Name><Val>{val}</Val></DBL>") == value


def test_refnum_kinds_are_read_in_either_place_and_written_before_val() -> None:
    kinds = "<RefKind>VI</RefKind><RefType>Control</RefType>"
    labview = f"<Refnum><Name>r</Name>{kinds}<Val>0x1</Val></Refnum>"
    schema = f"<Refnum><Name>r</Name><Val>0x1</Val>{kinds}</Refnum>"
    assert parse(labview) == parse(schema)
    assert (
        dump(parse(schema).values[0], newline="\n")
        .replace("\n", "")
        .startswith("<Refnum><Name>r</Name><RefKind>VI")
    )
    with pytest.raises(LVXMLError):
        parse(
            "<Refnum><Name>r</Name><RefKind>VI</RefKind><Val>0</Val><RefKind>VI</RefKind></Refnum>"
        )


def test_parse_reads_every_bytes_like_input_and_hints_at_the_code_page() -> None:
    data = string("x").encode()
    for given in (data, bytearray(data), memoryview(data)):
        assert from_lv_xml(given) == "x"
    with pytest.raises(LVXMLError, match="code page"):
        parse(string("\xe9").encode("cp1252"))
    with pytest.raises(LVXMLError, match="unknown encoding"):
        parse(b"<?xml version='1.0' encoding='nope'?>" + data)
    with pytest.raises(TypeError):
        parse(42)  # type: ignore[arg-type]


def test_schema_objects_check_themselves() -> None:
    with pytest.raises(ValueError, match="unknown scalar tag"):
        Array("FXP")
    with pytest.raises(ValueError, match="unknown scalar tag"):
        Cluster({"x": "Dbl"})
    with pytest.raises(TypeError):
        Cluster({"x": 3})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        Cluster({1: "DBL"})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        Array("DBL", True)
    with pytest.raises(TypeError):
        LVEnum(("a", 1))  # type: ignore[arg-type]
    fields = {"x": "DBL"}
    cluster = Cluster(fields)  # type: ignore[arg-type]
    fields["y"] = "I8"
    assert list(cluster.fields) == ["x"]
    assert LVEnum(["a", "b"]).choices == ("a", "b")  # type: ignore[arg-type]


def test_nodes_and_documents_check_their_field_types() -> None:
    node = Node("Cluster", "c", num_elts=0, items=[], extra=[])  # type: ignore[arg-type]
    assert node.items == () and node.extra == ()
    for bad in (
        {"val": 1},
        {"name": None},
        {"dims": (True,)},
        {"choices": "ab"},
        {"extra": (("a",),)},
    ):
        with pytest.raises(TypeError):
            Node("DBL", **bad)
    with pytest.raises(TypeError):
        Document((node,), wrapped=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Document(("x",))  # type: ignore[arg-type]
    assert Document([node]).items == (node,)  # type: ignore[arg-type]


def test_dump_checks_its_arguments() -> None:
    node = Node("I8", "n", val="1")
    assert dump(node, newline="\r") == "<I8>\r<Name>n</Name>\r<Val>1</Val>\r</I8>"
    for bad in ({"newline": "<x>"}, {"newline": ""}, {"indent": "x"}):
        with pytest.raises(ValueError):
            dump(node, **bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dump("<I8/>")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dump(node, declaration=1)  # type: ignore[arg-type]
    with pytest.raises(LVXMLError, match="U\\+D800"):
        dump(Node("String", "s", val="\ud800"))


def test_errors_are_bounded_located_and_pickle() -> None:
    with pytest.raises(LVXMLError) as info:
        from_lv_xml(f"<DBL><Name>{'n' * 5000}</Name><Val>{'9' * 5000}x</Val></DBL>")
    error = info.value
    assert len(str(error)) < 500 and len(error.message) < 300 and len(error.path) < 100
    again = pickle.loads(pickle.dumps(error))
    assert (again.message, again.path, str(again)) == (error.message, error.path, str(error))
    assert LVXMLError.__module__ == Node.__module__ == Document.__module__ == "lvxml"
    assert isinstance(error, ValueError)


def test_values_and_documents_round_trip() -> None:
    schema = Cluster({"x": "DBL", "m": LVEnum(("a", "b"), "EB"), "g": Array("I16", 2)})
    value = {"x": -0.5, "m": "b", "g": [[1, 2], [3, 4]]}
    text = to_lv_xml(value, schema, name="c")  # type: ignore[arg-type]
    assert from_lv_xml(text) == value and validate(text) == []
    node = to_node(value, schema, name="c")  # type: ignore[arg-type]
    assert to_value(node) == value
    wrapped = dump(Document((Node("Version", val="26.3.1f1"), node)))
    assert from_lv_xml_all(wrapped) == [value]
    assert validate(wrapped.replace("<Val>1</Val>", "<Val>9</Val>", 1))
    assert lvxml.__all__ and lvxml.__version__ == "1.0.0"

"""Plain-value encoding and decoding for every type `to_lv_xml` writes."""

from __future__ import annotations

import math

import pytest

from lvxml import Array, Cluster, LVEnum, LVXMLError, from_lv_xml, to_lv_xml, to_node
from lvxml._schema import Schema, Value

ROUND_TRIPS: list[tuple[Value, Schema]] = [
    (-128, "I8"),
    (2**64 - 1, "U64"),
    (0.1, "DBL"),
    (1.5, "SGL"),
    (1 / 3, "EXT"),
    (1 - 2j, "CDB"),
    (0.5j, "CSG"),
    (3 + 4j, "CXT"),
    (True, "Boolean"),
    ("C:\\data\\run.tdms", "Path"),
    ("Dev1/ai0", "DAQChannel"),
    ("line1\r\nline2\ttab <&> \"'", "String"),
    ("Run", LVEnum(("Idle", "Run"))),
    ([[1, 2, 3], [4, 5, 6]], Array("I32", 2)),
    ([[[1], [2]], [[3], [4]]], Array("U8", 3)),
    ([[], []], Array("DBL", 2)),
    ([], Array("DBL", 2)),
    ([{"a": "x"}, {"a": "y"}], Array(Cluster({"a": "String"}))),
    ({"m": [[True]], "e": "b"}, Cluster({"m": Array("Boolean", 2), "e": LVEnum(("a", "b"), "EL")})),
]


@pytest.mark.parametrize(("value", "schema"), ROUND_TRIPS)
def test_round_trip(value: Value, schema: Schema) -> None:
    assert from_lv_xml(to_lv_xml(value, schema, name="v")) == value


def test_enum_accepts_an_index_and_decodes_to_the_label() -> None:
    xml = to_lv_xml(1, LVEnum(("off", "on"), "EB"))
    assert "<EB>" in xml
    assert "<Choice>off</Choice>" in xml
    assert "<Val>1</Val>" in xml
    assert from_lv_xml(xml) == "on"


def test_complex_uses_labview_layout() -> None:
    assert "<Val>1.0 +-2.0 i</Val>" in to_lv_xml(1 - 2j, "CDB")


def test_two_dimensional_array_is_row_major() -> None:
    node = to_node([[1, 2], [3, 4]], Array("I16", 2))
    assert node.dims == (2, 2)
    assert [item.val for item in node.items] == ["1", "2", "3", "4"]


def test_empty_array_keeps_one_default_element() -> None:
    node = to_node([[], []], Array(LVEnum(("a",)), 2))
    assert node.dims == (2, 0)
    assert len(node.items) == 1
    assert node.items[0].val == "0"


def test_non_finite_floats_use_labview_spellings() -> None:
    xml = to_lv_xml([math.nan, math.inf, -math.inf], Array("DBL"))
    assert "<Val>NaN</Val>" in xml
    assert "<Val>Inf</Val>" in xml
    assert "<Val>-Inf</Val>" in xml
    values = from_lv_xml(xml)
    assert isinstance(values, list)
    assert math.isnan(values[0])  # type: ignore[arg-type]
    assert values[1:] == [math.inf, -math.inf]


def test_decimal_point_is_never_localized() -> None:
    assert "<Val>1234.5</Val>" in to_lv_xml(1234.5, "DBL")


@pytest.mark.parametrize(
    ("value", "schema", "message"),
    [
        ([[1, 2], [3]], Array("I32", 2), "ragged array"),
        ([1, 2], Array("I32", 2), "Array expects a list"),
        ("c", LVEnum(("a", "b")), "not one of the choices"),
        (2, LVEnum(("a", "b")), "outside 0..1"),
        (True, LVEnum(("a", "b")), "label or index"),
        (1e39, "SGL", "single precision"),
        ("1", "CDB", "expects a number"),
        (1, "Path", "expects a str"),
        (1.0, "FXP", "unknown scalar tag"),
        ({"x": 1.0, "y": 2.0}, Cluster({"x": "DBL"}), "unknown fields"),
    ],
)
def test_encoding_errors_are_honest(value: Value, schema: Schema, message: str) -> None:
    with pytest.raises(LVXMLError, match=message):
        to_lv_xml(value, schema)


def test_encoding_errors_carry_the_value_path() -> None:
    schema = Cluster({"data": Array("U8")})
    with pytest.raises(LVXMLError) as info:
        to_lv_xml({"data": [1, 300]}, schema, name="scan")
    assert info.value.path == "scan.data[1]"


def test_unwritable_characters_raise() -> None:
    with pytest.raises(LVXMLError, match="U\\+D800"):
        to_lv_xml("a\ud800b", "String")


def test_control_characters_are_written_raw_like_labview() -> None:
    assert "<Val>a\x00\x07b</Val>" in to_lv_xml("a\x00\x07b", "String")


@pytest.mark.parametrize(
    "build",
    [
        lambda: LVEnum(()),
        lambda: LVEnum(("a", "a")),
        lambda: LVEnum(("a",), "U8"),
        lambda: Array("DBL", 0),
        lambda: Array(Array("DBL")),
    ],
)
def test_schema_objects_reject_impossible_shapes(build: object) -> None:
    with pytest.raises(ValueError):
        build()  # type: ignore[operator]


def test_duplicate_cluster_names_are_not_silently_merged() -> None:
    xml = (
        "<Cluster><Name>c</Name><NumElts>2</NumElts>"
        "<I8><Name></Name><Val>1</Val></I8><I8><Name></Name><Val>2</Val></I8></Cluster>"
    )
    with pytest.raises(LVXMLError, match="duplicate field name"):
        from_lv_xml(xml)


def test_carriage_returns_inside_strings_survive_a_read() -> None:
    xml = "<String>\r\n<Name>s</Name>\r\n<Val>a\r\nb\rc</Val>\r\n</String>"
    assert from_lv_xml(xml) == "a\r\nb\rc"


def test_doctype_is_refused() -> None:
    with pytest.raises(LVXMLError, match="DOCTYPE"):
        from_lv_xml('<!DOCTYPE x [<!ENTITY e "y">]><String><Name/><Val>&e;</Val></String>')


def test_container_types_decode_to_lists_of_items() -> None:
    xml = "<LvVariant><Name>v</Name><I32><Name>n</Name><Val>4</Val></I32></LvVariant>"
    assert from_lv_xml(xml) == [4]
    stamp = (
        "<Timestamp><Name>t</Name><Cluster><Name/><NumElts>1</NumElts>"
        "<I64><Name>s</Name><Val>5</Val></I64></Cluster></Timestamp>"
    )
    assert from_lv_xml(stamp) == [{"s": 5}]


def test_refnum_decodes_to_its_val_text() -> None:
    xml = "<Refnum><Name>q</Name><RefKind>Queue</RefKind><Val>0x0000002a</Val></Refnum>"
    assert from_lv_xml(xml) == "0x0000002a"

import pytest

from lvxml import Array, Cluster, LVXMLError, from_lv_xml, to_lv_xml
from lvxml._schema import Value

DBL = "<DBL><Name>x</Name><Val>3.14000</Val></DBL>"
I32 = "<I32><Name>count</Name><Val>-7</Val></I32>"
BOOL = "<Boolean><Name>on</Name><Val>1</Val></Boolean>"
STRING = "<String><Name>label</Name><Val>hi &amp; bye</Val></String>"
ARRAY_DBL = (
    "<Array><Name>xs</Name><Dimsize>2</Dimsize>"
    "<DBL><Name></Name><Val>1.0</Val></DBL>"
    "<DBL><Name></Name><Val>2.5</Val></DBL></Array>"
)
CLUSTER = (
    "<Cluster><Name>pt</Name><NumElts>2</NumElts>"
    "<DBL><Name>x</Name><Val>1.0</Val></DBL>"
    "<I32><Name>y</Name><Val>5</Val></I32></Cluster>"
)


def test_parse_scalar_dbl() -> None:
    assert from_lv_xml(DBL) == pytest.approx(3.14)


def test_parse_scalar_i32() -> None:
    value = from_lv_xml(I32)
    assert value == -7
    assert isinstance(value, int)


def test_parse_boolean() -> None:
    assert from_lv_xml(BOOL) is True
    assert from_lv_xml(BOOL.replace("<Val>1</Val>", "<Val>0</Val>")) is False


def test_parse_string_unescapes_entities() -> None:
    assert from_lv_xml(STRING) == "hi & bye"


def test_parse_array_of_dbl() -> None:
    assert from_lv_xml(ARRAY_DBL) == [1.0, 2.5]


def test_parse_cluster_keeps_named_fields() -> None:
    assert from_lv_xml(CLUSTER) == {"x": 1.0, "y": 5}


def test_parse_strips_lvdata_wrapper() -> None:
    wrapped = f'<LVData xmlns="http://www.ni.com/LVData"><Version>21.0</Version>{DBL}</LVData>'
    assert from_lv_xml(wrapped) == pytest.approx(3.14)


def test_round_trip_scalar() -> None:
    assert from_lv_xml(to_lv_xml(42, "I16", name="n")) == 42


def test_round_trip_string_with_markup() -> None:
    assert from_lv_xml(to_lv_xml("<a> & 'b'", "String")) == "<a> & 'b'"


def test_round_trip_array() -> None:
    schema = Array("DBL")
    assert from_lv_xml(to_lv_xml([1.0, 2.5, 3.0], schema)) == [1.0, 2.5, 3.0]


def test_round_trip_empty_array_uses_dimsize_zero() -> None:
    xml = to_lv_xml([], Array("I32"))
    assert "<Dimsize>0</Dimsize>" in xml
    assert from_lv_xml(xml) == []


def test_round_trip_cluster() -> None:
    schema = Cluster({"x": "DBL", "flag": "Boolean", "tag": "String"})
    value: Value = {"x": 1.5, "flag": True, "tag": "ok"}
    assert from_lv_xml(to_lv_xml(value, schema)) == value


def test_round_trip_nested_cluster_of_array() -> None:
    schema = Cluster({"name": "String", "data": Array("U8")})
    value: Value = {"name": "scan", "data": [0, 255, 7]}
    assert from_lv_xml(to_lv_xml(value, schema)) == value


def test_unknown_tag_raises() -> None:
    with pytest.raises(LVXMLError):
        from_lv_xml("<Variant><Name></Name><Val>?</Val></Variant>")


def test_malformed_xml_raises() -> None:
    with pytest.raises(LVXMLError):
        from_lv_xml("<DBL><Name>x</Name><Val>1.0")


def test_missing_val_raises() -> None:
    with pytest.raises(LVXMLError):
        from_lv_xml("<DBL><Name>x</Name></DBL>")


def test_array_with_fewer_elements_than_its_dimsizes_raises() -> None:
    xml = "<Array><Name>m</Name><Dimsize>1</Dimsize><Dimsize>1</Dimsize></Array>"
    with pytest.raises(LVXMLError):
        from_lv_xml(xml)


def test_array_dimsize_mismatch_raises() -> None:
    xml = "<Array><Name></Name><Dimsize>3</Dimsize><I8><Name></Name><Val>1</Val></I8></Array>"
    with pytest.raises(LVXMLError):
        from_lv_xml(xml)


def test_integer_out_of_range_raises() -> None:
    with pytest.raises(LVXMLError):
        to_lv_xml(999, "U8")


def test_wrong_python_type_for_schema_raises() -> None:
    with pytest.raises(LVXMLError):
        to_lv_xml("not a number", "DBL")


def test_cluster_missing_field_raises() -> None:
    with pytest.raises(LVXMLError):
        to_lv_xml({"x": 1.0}, Cluster({"x": "DBL", "y": "DBL"}))

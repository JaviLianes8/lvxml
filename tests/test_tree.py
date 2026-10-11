"""The lossless typed tree: parse, dump and the JSON dict form."""

from __future__ import annotations

import pytest

from lvxml import (
    LVDATA_NAMESPACE,
    Document,
    LVXMLError,
    Node,
    dump,
    from_lv_xml_all,
    parse,
    to_value,
)

WRAPPED = (
    "<?xml version='1.0' standalone='yes' ?>\r\n"
    '<LVData xmlns="http://www.ni.com/LVData">\r\n'
    "<Version>26.3.1f1</Version>\r\n"
    '<String>\r\n<Name>s</Name>\r\n<Val>a &lt;b&gt; &amp; "q"</Val>\r\n</String>\r\n'
    "<EW>\r\n<Name>e</Name>\r\n<Choice>x</Choice>\r\n<Choice>y</Choice>\r\n"
    "<Val>1</Val>\r\n</EW>\r\n"
    "</LVData>"
)


def test_parse_keeps_every_part() -> None:
    document = parse(WRAPPED)
    assert document.wrapped
    assert document.namespace == LVDATA_NAMESPACE
    assert document.version == "26.3.1f1"
    text, enum = document.values
    assert text == Node("String", "s", val='a <b> & "q"')
    assert enum == Node("EW", "e", val="1", choices=("x", "y"))


def test_dump_reproduces_labview_layout_exactly() -> None:
    assert dump(parse(WRAPPED)) == WRAPPED


def test_raw_val_text_is_kept_verbatim() -> None:
    document = parse("<DBL><Name>x</Name><Val>0.50000000000000</Val></DBL>")
    assert document.values[0].val == "0.50000000000000"
    assert to_value(document.values[0]) == 0.5


def test_bare_node_dumps_without_declaration() -> None:
    node = Node("I32", "n", val="7")
    assert dump(node, newline="\n") == "<I32>\n<Name>n</Name>\n<Val>7</Val>\n</I32>"
    bare = parse(dump(node))
    assert not bare.wrapped
    assert bare.namespace is None
    assert bare.values == (node,)


def test_dump_options() -> None:
    node = Node("Boolean", "b", val="1")
    text = dump(node, newline="\n", indent="  ", declaration=True)
    assert text.splitlines() == [
        "<?xml version='1.0' standalone='yes' ?>",
        "<Boolean>",
        "  <Name>b</Name>",
        "  <Val>1</Val>",
        "</Boolean>",
    ]


def test_refnum_extra_fields_round_trip() -> None:
    text = (
        "<Refnum><Name>r</Name><Val>0x1</Val><RefKind>VI</RefKind><RefType>Control</RefType>"
        "<ActiveXType><GUID>{0}</GUID></ActiveXType><DotNetType><Name>N</Name></DotNetType></Refnum>"
    )
    node = parse(text).values[0]
    assert node.extra == (
        ("RefKind", "VI"),
        ("RefType", "Control"),
        ("ActiveXType.GUID", "{0}"),
        ("DotNetType.Name", "N"),
    )
    assert parse(dump(node)).values[0] == node


def test_lvdata_with_several_values() -> None:
    text = (
        "<LVData><Version>1</Version><I8><Name>a</Name><Val>1</Val></I8>"
        "<I8><Name>b</Name><Val>2</Val></I8></LVData>"
    )
    assert from_lv_xml_all(text) == [1, 2]
    assert parse(text).namespace is None


@pytest.mark.parametrize(
    "node",
    [
        Node("DBL", "x"),
        Node("DBL", "x", val="1", items=(Node("I8", val="1"),)),
        Node("Array", "a"),
        Node("Array", "a", dims=(1,), items=(Node("Array", dims=(0,)),)),
        Node("Cluster", "c"),
        Node("EW", "e", val="0"),
        Node("Timestamp", "t", items=(Node("DBL", val="1"),)),
        Node("Refnum", "r", val="0", extra=(("RefType", "VI"),)),
        Node("Refnum", "r", val="0", extra=(("Bogus", "x"),)),
        Node("FXP", "f", val="1"),
    ],
)
def test_dump_refuses_nodes_the_schema_cannot_express(node: Node) -> None:
    with pytest.raises(LVXMLError):
        dump(node)


def test_document_dict_round_trip_and_checks() -> None:
    document = parse(WRAPPED)
    assert Document.from_dict(document.to_dict()) == document
    assert Node.from_dict(document.values[1].to_dict()) == document.values[1]


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"items": "x"},
        {"items": [], "wrapped": "yes"},
        {"items": [{"tag": 3}]},
        {"items": [{"tag": "DBL", "name": "x", "val": 1}]},
        {"items": [{"tag": "DBL", "name": "x", "val": "1", "colour": "red"}]},
        {"items": [{"tag": "Array", "name": "a", "dims": [-1], "items": []}]},
        {"items": [{"tag": "Cluster", "name": "c", "num_elts": True, "items": []}]},
        {"wrapped": False, "items": []},
    ],
)
def test_document_from_dict_rejects_bad_shapes(data: object) -> None:
    with pytest.raises(LVXMLError):
        Document.from_dict(data)

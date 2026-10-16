"""Contracts added for the survivors of the independent reviewer's mutation round."""

from __future__ import annotations

import io

import pytest

from lvxml import Cluster, LVXMLError, Node, dump, from_lv_xml, to_node, validate
from lvxml._cliio import say

PRIVATE = chr(0xE000) + chr(0xE021) + "\x01"


def test_private_use_characters_next_to_the_escape_range_survive() -> None:
    assert from_lv_xml(f"<String><Name>s</Name><Val>{PRIVATE}</Val></String>") == PRIVATE


def test_a_byte_order_mark_and_spaces_may_precede_the_declaration() -> None:
    text = chr(0xFEFF) + " \n<?xml version='1.0'?><I8><Name>n</Name><Val>1</Val></I8>"
    assert from_lv_xml(text) == 1


@pytest.mark.parametrize("size", ["\t1", "1\n", "\xa01"], ids=["tab", "newline", "nbsp"])
@pytest.mark.parametrize("field", ["Dimsize", "NumElts"])
def test_counts_allow_spaces_only(field: str, size: str) -> None:
    item = "<I8><Name></Name><Val>1</Val></I8>"
    tag = "Array" if field == "Dimsize" else "Cluster"
    with pytest.raises(LVXMLError):
        from_lv_xml(f"<{tag}><Name>a</Name><{field}>{size}</{field}>{item}</{tag}>")
    assert from_lv_xml(f"<{tag}><Name>a</Name><{field}> 1 </{field}>{item}</{tag}>")


def test_a_complex_value_needs_the_plus_separator() -> None:
    with pytest.raises(LVXMLError):
        from_lv_xml("<CDB><Name>c</Name><Val>1 -2 i</Val></CDB>")
    assert from_lv_xml("<CDB><Name>c</Name><Val>1 +-2 i</Val></CDB>") == 1 - 2j


def test_an_empty_shape_too_large_to_count_is_reported_as_too_many_lists() -> None:
    sizes = "".join(f"<Dimsize>{d}</Dimsize>" for d in (2**62, 4, 0))
    problems = validate(f"<Array><Name>a</Name>{sizes}<I8><Name></Name><Val>0</Val></I8></Array>")
    assert len(problems) == 1 and "lists" in problems[0]


def test_dump_indents_with_tabs() -> None:
    expected = "<I8>\n\t<Name>n</Name>\n\t<Val>1</Val>\n</I8>"
    assert dump(Node("I8", "n", val="1"), newline="\n", indent="\t") == expected


def test_a_cut_command_line_ends_with_a_marker() -> None:
    stream = io.StringIO()
    say(stream, "x" * 1000)
    assert stream.getvalue() == "x" * 296 + " ...\n"


def test_unknown_cluster_fields_of_any_key_type_are_an_lvxml_error() -> None:
    with pytest.raises(LVXMLError, match="unknown fields"):
        to_node({1: 0, "b": 0, "a": 1}, Cluster({"a": "I8"}))  # type: ignore[dict-item]

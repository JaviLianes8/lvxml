"""Contracts from the blind mutation round of the contract-strength lens: limits and bounds."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from lvxml import Document, LVEnum, LVXMLError, Node, from_lv_xml, parse, to_node, validate


def fails(call: Callable[[], object]) -> LVXMLError:
    with pytest.raises(LVXMLError) as info:
        call()
    return info.value


def test_a_value_of_exactly_40_characters_is_quoted_whole() -> None:
    text = "a" * 40
    error = fails(lambda: from_lv_xml(f"<DBL><Name>x</Name><Val>{text}</Val></DBL>"))
    assert repr(text) in error.message and "characters)" not in error.message


def test_a_name_of_exactly_40_characters_is_kept_whole_in_the_path() -> None:
    name = "n" * 40
    error = fails(lambda: from_lv_xml(f"<I8><Name>{name}</Name><Val>300</Val></I8>"))
    assert error.path == f"I8[{name}]"


def test_quoted_attribute_lists_are_cut_to_40_characters() -> None:
    attrs = " ".join(f'a{i}="1"' for i in range(30))
    error = fails(lambda: parse(f"<I8 {attrs}><Name>n</Name><Val>1</Val></I8>"))
    assert "a29" not in error.message and "..." in error.message


def test_a_message_of_exactly_200_characters_is_not_cut() -> None:
    assert LVXMLError("m" * 200).message == "m" * 200


def test_extra_pairs_must_have_exactly_two_parts() -> None:
    with pytest.raises(TypeError):
        Node("Refnum", "r", val="0x1", extra=(("RefKind", "a", "b"),))  # type: ignore[arg-type]


def test_a_document_namespace_must_be_str_or_none() -> None:
    with pytest.raises(TypeError):
        Document((Node("I8", "n", val="1"),), namespace=5)  # type: ignore[arg-type]


def test_complex_single_overflow_is_refused() -> None:
    assert "single precision" in fails(lambda: to_node(complex(1e39, 0), "CSG")).message


def test_number_text_of_exactly_the_limit_is_read() -> None:
    assert from_lv_xml(f"<DBL><Name>x</Name><Val>{'0' * 999}1</Val></DBL>") == 1.0


def test_version_is_the_first_header() -> None:
    items = (Node("Version", val="a"), Node("Version", val="b"), Node("I8", "n", val="1"))
    assert Document(items).version == "a"


BOUNDS = [
    ("I8", -(2**7), 2**7 - 1),
    ("I16", -(2**15), 2**15 - 1),
    ("I32", -(2**31), 2**31 - 1),
    ("I64", -(2**63), 2**63 - 1),
    ("U8", 0, 2**8 - 1),
    ("U16", 0, 2**16 - 1),
    ("U32", 0, 2**32 - 1),
    ("U64", 0, 2**64 - 1),
]


@pytest.mark.parametrize(("tag", "low", "high"), BOUNDS)
def test_every_integer_bound_is_inclusive_and_one_past_is_refused(
    tag: str, low: int, high: int
) -> None:
    def xml(value: int) -> str:
        return f"<{tag}><Name>n</Name><Val>{value}</Val></{tag}>"

    assert from_lv_xml(xml(low)) == low and from_lv_xml(xml(high)) == high
    fails(lambda: from_lv_xml(xml(low - 1)))
    fails(lambda: from_lv_xml(xml(high + 1)))
    assert to_node(low, tag).val == str(low) and to_node(high, tag).val == str(high)
    fails(lambda: to_node(high + 1, tag))


@pytest.mark.parametrize(("tag", "most"), [("EB", 256), ("EW", 65536)])
def test_the_enum_choice_count_limit(tag: str, most: int) -> None:
    assert len(LVEnum([str(i) for i in range(most)], tag).choices) == most  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        LVEnum([str(i) for i in range(most + 1)], tag)  # type: ignore[arg-type]


def test_reftype_after_val_names_the_labview_rule() -> None:
    xml = "<Refnum><Name>r</Name><Val>0x1</Val><RefType>t</RefType></Refnum>"
    assert "before <Val>" in fails(lambda: parse(xml)).message


def test_every_descendant_must_share_the_root_namespace() -> None:
    fails(
        lambda: parse(
            "<Cluster><Name>c</Name><NumElts>1</NumElts>"
            "<I8><Name xmlns='urn:x'>n</Name><Val>1</Val></I8></Cluster>"
        )
    )


def test_one_hundred_dimensions_are_read() -> None:
    sizes = "<Dimsize>1</Dimsize>" * 100
    value: Any = from_lv_xml(
        f"<Array><Name>a</Name>{sizes}<I8><Name></Name><Val>5</Val></I8></Array>"
    )
    for _ in range(99):
        value = value[0]
    assert value == [5]


def test_attributes_on_lvdata_are_refused() -> None:
    fails(lambda: parse('<LVData a="1"><Version>1</Version></LVData>'))


def test_dimsize_takes_ascii_digits_only() -> None:
    digit = chr(0x661)
    fails(
        lambda: parse(
            f"<Array><Name>a</Name><Dimsize>{digit}</Dimsize>"
            "<I8><Name></Name><Val>1</Val></I8></Array>"
        )
    )


def test_a_declared_code_page_does_not_apply_to_text() -> None:
    e = chr(0xE9)
    xml = f"<?xml version='1.0' encoding='cp1252'?><String><Name>s</Name><Val>{e}</Val></String>"
    assert from_lv_xml(xml) == e


def test_text_before_the_declaration_may_be_whitespace() -> None:
    assert from_lv_xml("\r\n <?xml version='1.0'?><I8><Name>n</Name><Val>1</Val></I8>") == 1


def test_an_empty_array_holds_at_most_one_default_element() -> None:
    two = "<I8><Name></Name><Val>0</Val></I8>" * 2
    assert validate(f"<Array><Name>a</Name><Dimsize>0</Dimsize>{two}</Array>")


def test_a_refnum_needs_hex_digits_and_allows_spaces_but_not_tabs() -> None:
    assert validate("<Refnum><Name>r</Name><Val>0x</Val></Refnum>")
    assert validate("<Refnum><Name>r</Name><Val> 0x1 </Val></Refnum>") == []
    assert validate("<Refnum><Name>r</Name><Val>\t0x1</Val></Refnum>")


def test_exactly_the_most_empty_rows_is_read() -> None:
    xml = (
        "<Array><Name>a</Name><Dimsize>100000</Dimsize><Dimsize>0</Dimsize>"
        "<I8><Name></Name><Val>0</Val></I8></Array>"
    )
    value: Any = from_lv_xml(xml)
    assert len(value) == 100000 and value[0] == []


def test_integer_text_past_twenty_digits_is_quoted_not_converted() -> None:
    error = fails(lambda: from_lv_xml(f"<I64><Name>n</Name><Val>{'9' * 21}</Val></I64>"))
    assert error.message.startswith("'999")

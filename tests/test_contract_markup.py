"""Contracts from the third contract-strength round: how markup is told apart from text."""

from __future__ import annotations

import time

import pytest

from lvxml import LVXMLError, from_lv_xml, parse

VERSION = "<Version>1</Version>"


@pytest.mark.parametrize(
    ("root", "namespace"),
    [
        ("<LVData xmlns='a>&apos;b'>", "a>'b"),
        ('<LVData\r\n xmlns="a&quot;b"\r\n>', 'a"b'),
        ('<LVData\n xmlns="a&quot;b"\n>', 'a"b'),
        ('<LVData xmlns="a\r\n&quot;b">', 'a "b'),
    ],
    ids=["single-quoted", "crlf-in-tag", "lf-in-tag", "crlf-in-value"],
)
def test_the_namespace_tag_may_use_any_quote_and_line_break(root: str, namespace: str) -> None:
    assert parse(f"{root}{VERSION}</LVData>").namespace == namespace


@pytest.mark.parametrize("quote", ['"', "'"])
def test_a_quoted_child_tag_ends_at_its_own_greater_than(quote: str) -> None:
    text = (
        f'<LVData xmlns="n">{VERSION}<String><Name>s</Name>'
        f"<Val xmlns={quote}n{quote}>a\r>b &amp;</Val></String></LVData>"
    )
    assert parse(text).items[1].val == "a\r>b &"


@pytest.mark.parametrize("extra", ["<!-- a < b -->", "<?pi a<b?>"], ids=["comment", "pi"])
@pytest.mark.parametrize("where", ["before", "after"])
def test_markup_holding_a_less_than_sign_outside_the_root_is_read(extra: str, where: str) -> None:
    value = "<String><Name>s</Name><Val>a\r\nb</Val></String>"
    text = f"{extra}\r\n{value}" if where == "before" else f"{value}\r\n{extra}\r\n"
    assert from_lv_xml(text) == "a\r\nb"


def test_a_comment_inside_a_value_keeps_its_text_and_carriage_returns() -> None:
    text = "<String><Name>s</Name><Val>a\r<!-- x < \" ' & -->b &amp;</Val></String>"
    assert from_lv_xml(text) == "a\rb &"


@pytest.mark.parametrize("text", ["<!-- open <I8/>", "<I8/><?pi open", "--><!--<I8/>"])
def test_a_comment_or_instruction_never_closed_is_refused(text: str) -> None:
    with pytest.raises(LVXMLError, match="never closed"):
        parse(text)


@pytest.mark.parametrize("unit", ["<", '<"', "<'", '<a "', "<!--", "<?", "-->", "<!-- <"], ids=str)
def test_hostile_markup_runs_stay_linear(unit: str) -> None:
    times = []
    for count in (5_000, 20_000):
        text = unit * count + "\r&"
        started = time.perf_counter()
        with pytest.raises(LVXMLError):
            parse(text)
        times.append(time.perf_counter() - started)
    assert times[1] < max(times[0], 0.002) * 4 * 3

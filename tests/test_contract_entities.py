"""Contracts from the second contract-strength round: entities, markup and byte order marks."""

from __future__ import annotations

import time

import pytest

from lvxml import LVXMLError, from_lv_xml, parse

VALUE = "<String><Name>s</Name><Val>a</Val></String>"


@pytest.mark.parametrize("text", [f"x & y{VALUE}", f"{VALUE}x & y"], ids=["before", "after"])
def test_text_with_an_ampersand_outside_the_root_is_refused(text: str) -> None:
    with pytest.raises(LVXMLError):
        from_lv_xml(text)


@pytest.mark.parametrize(
    ("written", "namespace"),
    [
        ("a&#65;&#x42;", "aAB"),
        ("a&apos;b", "a'b"),
        ("a&lt;&gt;&quot;", 'a<>"'),
        ("a>&quot;b", 'a>"b'),
    ],
    ids=["references", "apos", "named", "greater-than"],
)
@pytest.mark.parametrize(
    "prolog", ["", "<?xml version='1.0'?>\n<!-- c -->\n"], ids=["bare", "prolog"]
)
def test_the_namespace_reads_every_xml_entity(prolog: str, written: str, namespace: str) -> None:
    text = f'{prolog}<LVData xmlns="{written}"><Version>1</Version></LVData>'
    assert parse(text).namespace == namespace


def test_a_lone_ampersand_in_the_namespace_is_refused() -> None:
    with pytest.raises(LVXMLError):
        parse('<LVData xmlns="a&b"><Version>1</Version></LVData>')


@pytest.mark.parametrize("val", ["&lt &amp &gtx", "&AMP; &Lt; &GT;"], ids=["no-semicolon", "case"])
def test_only_the_exact_three_entities_are_decoded(val: str) -> None:
    assert from_lv_xml(f"<String><Name>s</Name><Val>{val}</Val></String>") == val


def test_a_byte_order_mark_after_the_stripped_one_is_still_read() -> None:
    assert from_lv_xml(b"\xef\xbb\xbf\xef\xbb\xbf" + VALUE.encode()) == "a"


@pytest.mark.parametrize(
    "unit", ['<"', "<'", '<a "', "<a='"], ids=["double", "single", "attr", "unclosed"]
)
def test_unclosed_quotes_in_markup_stay_linear(unit: str) -> None:
    times = []
    for count in (5_000, 20_000):
        text = "<I8>" + unit * count + "\r&</I8>"
        started = time.perf_counter()
        with pytest.raises(LVXMLError):
            parse(text)
        times.append(time.perf_counter() - started)
    assert times[1] < max(times[0], 0.002) * 4 * 3

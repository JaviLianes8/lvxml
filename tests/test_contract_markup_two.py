"""Contracts from the fourth contract-strength round: comments and instructions around values."""

from __future__ import annotations

import time

import pytest

from lvxml import LVXMLError, from_lv_xml
from lvxml._load import split_markup

VALUE = "<String><Name>s</Name><Val>a\r\nb &c</Val></String>"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("<!--\r\n a < b\r\n-->", ""),
        ("<!-- a -->", "<!-- b -->"),
        ("<?pi a?>", "<?pi b?>"),
        ("<!-- a -> b < c -->", ""),
        ("<?pi a > b < c ?>", ""),
        ("<!-- a > b < c -->", ""),
        ("<!---->", "<!-- b -->"),
    ],
    ids=["multiline", "two-comments", "two-instructions", "arrow", "pi-gt", "comment-gt", "empty"],
)
def test_comments_and_instructions_around_the_root_are_read(before: str, after: str) -> None:
    assert from_lv_xml(f"{before}\r\n{VALUE}\r\n{after}\r\n") == "a\r\nb &c"


@pytest.mark.parametrize(
    "markup",
    ["<!-- see <? here -->", "<?pi <!-- x ?>"],
    ids=["pi-opener-in-comment", "comment-opener-in-pi"],
)
@pytest.mark.parametrize("where", ["before", "after"])
def test_an_opener_inside_other_markup_is_not_an_unclosed_one(markup: str, where: str) -> None:
    text = f"{markup}\r\n{VALUE}" if where == "before" else f"{VALUE}\r\n{markup}\r\n"
    assert from_lv_xml(text) == "a\r\nb &c"


@pytest.mark.parametrize(
    ("prefix", "unit", "suffix"),
    [("<!-- x -->", "<!--", ""), ("<?x y?>", "<?", ""), ("", "<?a", ">"), ("", "<a", "")],
    ids=["comment-after-closed", "instruction-after-closed", "instruction-then-gt", "open-tags"],
)
def test_unclosed_markup_after_closed_markup_is_refused_in_linear_time(
    prefix: str, unit: str, suffix: str
) -> None:
    times = []
    for count in (2_000, 8_000):
        text = prefix + unit * count + suffix + "\r&"
        started = time.perf_counter()
        with pytest.raises(LVXMLError):
            from_lv_xml(text)
        times.append(time.perf_counter() - started)
    assert times[1] < max(times[0], 0.002) * 4 * 3


def test_the_split_alternates_text_and_markup_and_a_tag_holds_no_less_than() -> None:
    parts = split_markup("a < b<!-- <? -->c<?p <!-- ?><d e='>' f=\"<\">g")
    assert parts == ["a < b", "<!-- <? -->", "c", "<?p <!-- ?>", "<d e='>' f=\"<\">g"]
    assert "".join(parts) == "a < b<!-- <? -->c<?p <!-- ?><d e='>' f=\"<\">g"


@pytest.mark.parametrize(
    ("text", "parts"),
    [
        ("<d e='<'>", ["<d e='<'>"]),
        ("x<a+b>y", ["x", "<a+b>", "y"]),
        ("<<b>", ["<", "<b>", ""]),
        ("<!-a<b-->", ["<!-a", "<b-->", ""]),
        ("<!-->a<b-->", ["", "<!-->a<b-->", ""]),
    ],
    ids=[
        "less-than-in-single-quotes",
        "any-tag-character",
        "stray-then-tag",
        "not-a-comment",
        "comment-opening-with-arrow",
    ],
)
def test_the_split_follows_xml_markup_rules(text: str, parts: list[str]) -> None:
    assert split_markup(text) == parts


def test_a_comment_whose_text_starts_with_greater_than_is_read() -> None:
    assert from_lv_xml(f"<!-->a<b-->\r\n{VALUE}") == "a\r\nb &c"

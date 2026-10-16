"""Contracts added for the findings of the independent QA lenses."""

from __future__ import annotations

import errno
import io
import sys
import typing

import pytest
from conftest import REAL_FILES

import lvxml
from lvxml import Array, Cluster, LVEnum, Node, dump, from_lv_xml, to_value
from lvxml._cli import main


class _ClosedReader(io.BytesIO):
    """A stdout buffer whose reader went away, as Windows reports it."""

    def write(self, data: object) -> int:
        raise OSError(errno.EINVAL, "Invalid argument")


class _Stdout:
    def __init__(self) -> None:
        self.buffer = _ClosedReader()
        self.encoding = "utf-8"

    def fileno(self) -> int:
        raise io.UnsupportedOperation("no file descriptor")


def test_a_reader_that_went_away_ends_quietly_with_status_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", _Stdout())
    assert main(["to-json", str(REAL_FILES[0])]) == 1
    assert capsys.readouterr().err == ""


def test_other_output_errors_are_still_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    class Full(_ClosedReader):
        def write(self, data: object) -> int:
            raise OSError(errno.ENOSPC, "No space left on device")

    stdout = _Stdout()
    stdout.buffer = Full()
    monkeypatch.setattr(sys, "stdout", stdout)
    errors = io.StringIO()
    monkeypatch.setattr(sys, "stderr", errors)
    assert main(["to-json", str(REAL_FILES[0])]) == 1
    assert "No space left" in errors.getvalue()


@pytest.mark.parametrize("bad", ["<I8/>", None, {"tag": "I8"}])
def test_to_value_and_dump_take_only_trees(bad: object) -> None:
    with pytest.raises(TypeError):
        to_value(bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dump(bad)  # type: ignore[arg-type]


def test_dump_checks_shape_but_writes_values_as_they_are() -> None:
    assert "<Val>300</Val>" in dump(Node("I8", "n", val="300"))
    with pytest.raises(lvxml.LVXMLError, match="out of range"):
        to_value(Node("I8", "n", val="300"))


def test_refnum_kinds_stay_together_with_refkind_first() -> None:
    for split in (
        "<RefKind>K</RefKind><Val>0</Val><RefType>T</RefType>",
        "<RefType>T</RefType><RefKind>K</RefKind><Val>0</Val>",
    ):
        with pytest.raises(lvxml.LVXMLError):
            from_lv_xml(f"<Refnum><Name>f</Name>{split}</Refnum>")


def test_every_public_class_reports_the_package_and_the_type_aliases_are_public() -> None:
    for cls in (Array, Cluster, LVEnum, Node, lvxml.Document, lvxml.LVXMLError):
        assert cls.__module__ == "lvxml"
        typing.get_type_hints(cls)
    assert lvxml.Schema is not None and lvxml.Value is not None
    value: lvxml.Value = from_lv_xml("<I8><Name>n</Name><Val>1</Val></I8>")
    assert value == 1


@pytest.mark.parametrize(
    "xml",
    [
        "<Boolean><Name>b</Name><Val>TAB1</Val></Boolean>",
        "<Boolean><Name>b</Name><Val>1CRLF</Val></Boolean>",
        "<EW><Name>e</Name><Choice>a</Choice><Choice>b</Choice><Val>TAB1</Val></EW>",
        "<EW><Name>e</Name><Choice>a</Choice><Choice>b</Choice><Val>+1</Val></EW>",
        "<I32><Name>n</Name><Val>+1</Val></I32>",
        "<DBL><Name>x</Name><Val>InfTAB</Val></DBL>",
        "<DBL><Name>x</Name><Val>NBSP1</Val></DBL>",
        "<Refnum><Name>r</Name><Val>12</Val></Refnum>",
    ],
)
def test_spellings_labview_2026_refuses_are_refused(xml: str) -> None:
    text = xml.replace("TAB", "\t").replace("CRLF", "\r\n").replace("NBSP", "\xa0")
    with pytest.raises(lvxml.LVXMLError):
        from_lv_xml(text)
    assert lvxml.validate(text)


def test_spaces_around_numbers_are_allowed_as_labview_allows_them() -> None:
    assert from_lv_xml("<Boolean><Name>b</Name><Val> 1 </Val></Boolean>") is True
    assert from_lv_xml("<DBL><Name>x</Name><Val> 2.5 </Val></DBL>") == 2.5
    assert from_lv_xml("<Refnum><Name>r</Name><Val> 0x12345678 </Val></Refnum>") == " 0x12345678 "


def test_version_must_come_first_and_validate_asks_for_one() -> None:
    value = "<I8><Name>n</Name><Val>1</Val></I8>"
    with pytest.raises(lvxml.LVXMLError, match="must come before"):
        lvxml.parse(f"<LVData>{value}<Version>1</Version></LVData>")
    assert lvxml.validate(f"<LVData><Version>1</Version>{value}</LVData>") == []
    assert lvxml.validate(f"<LVData>{value}</LVData>") == [
        "LVData: no <Version> header; LabVIEW's file reader refuses such a file"
    ]
    assert lvxml.validate(value) == []

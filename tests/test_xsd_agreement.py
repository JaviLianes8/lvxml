"""The reader rejects what the XSD rejects, and the extra value checks are named."""

from __future__ import annotations

import pytest
from xsd_check import xsd_valid

import lvxml

# Each sample breaks one rule of LVXMLSchema.xsd.
XSD_INVALID = {
    "val before name": "<DBL><Val>1</Val><Name>x</Name></DBL>",
    "missing name": "<DBL><Val>1</Val></DBL>",
    "missing val": "<DBL><Name>x</Name></DBL>",
    "two vals": "<I32><Name>x</Name><Val>1</Val><Val>2</Val></I32>",
    "unknown element": "<FXP><Name>x</Name><Val>1</Val></FXP>",
    "array in array": (
        "<Array><Name>a</Name><Dimsize>1</Dimsize>"
        "<Array><Name></Name><Dimsize>0</Dimsize></Array></Array>"
    ),
    "array without dimsize": "<Array><Name>a</Name></Array>",
    "cluster without numelts": "<Cluster><Name>c</Name></Cluster>",
    "enum without choice": "<EW><Name>e</Name><Val>0</Val></EW>",
    "timestamp holding a number": (
        "<Timestamp><Name>t</Name><DBL><Name/><Val>1</Val></DBL></Timestamp>"
    ),
    "reftype without refkind": "<Refnum><Name>r</Name><Val>0</Val><RefType>VI</RefType></Refnum>",
    "dotnet without name": "<Refnum><Name>r</Name><Val>0</Val><DotNetType></DotNetType></Refnum>",
    "stray text": "<Cluster><Name>c</Name>oops<NumElts>0</NumElts></Cluster>",
    "attribute": '<DBL unit="V"><Name>x</Name><Val>1</Val></DBL>',
    "child in another namespace": (
        "<Cluster><Name>c</Name><NumElts>1</NumElts>"
        '<I8 xmlns="urn:other"><Name>a</Name><Val>1</Val></I8></Cluster>'
    ),
    "child inside val": "<String><Name>s</Name><Val><b>x</b></Val></String>",
}

# Each sample is valid against the XSD but inconsistent as LabVIEW data.
XSD_VALID_BUT_INCONSISTENT = {
    "numelts mismatch": (
        "<Cluster><Name>c</Name><NumElts>2</NumElts><I8><Name>a</Name><Val>1</Val></I8></Cluster>",
        "NumElts 2 does not match 1",
    ),
    "dimsize mismatch": (
        "<Array><Name>a</Name><Dimsize>2</Dimsize><I8><Name/><Val>1</Val></I8></Array>",
        "needs 2 elements, found 1",
    ),
    "not a number": ("<DBL><Name>x</Name><Val>one</Val></DBL>", "invalid float"),
    "comma decimal": ("<DBL><Name>x</Name><Val>1,5</Val></DBL>", "always a period"),
    "out of range": ("<U8><Name>x</Name><Val>256</Val></U8>", "out of range for U8"),
    "enum index past choices": (
        "<EB><Name>e</Name><Choice>a</Choice><Val>1</Val></EB>",
        "past its 1 choices",
    ),
    "bad boolean": ("<Boolean><Name>b</Name><Val>yes</Val></Boolean>", "invalid boolean"),
    "bad complex": ("<CDB><Name>z</Name><Val>1.0</Val></CDB>", "invalid complex"),
    "mixed array": (
        "<Array><Name>a</Name><Dimsize>2</Dimsize>"
        "<I8><Name/><Val>1</Val></I8><U8><Name/><Val>1</Val></U8></Array>",
        "mixes element types",
    ),
}


@pytest.mark.parametrize("text", XSD_INVALID.values(), ids=list(XSD_INVALID))
def test_xsd_and_reader_both_reject(text: str) -> None:
    assert not xsd_valid(text)
    with pytest.raises(lvxml.LVXMLError):
        lvxml.parse(text)
    assert len(lvxml.validate(text)) == 1


@pytest.mark.parametrize(
    ("text", "message"),
    XSD_VALID_BUT_INCONSISTENT.values(),
    ids=list(XSD_VALID_BUT_INCONSISTENT),
)
def test_consistency_checks_go_beyond_the_xsd(text: str, message: str) -> None:
    assert xsd_valid(text)
    lvxml.parse(text)
    problems = lvxml.validate(text)
    assert len(problems) == 1
    assert message in problems[0]
    with pytest.raises(lvxml.LVXMLError, match=message):
        lvxml.from_lv_xml(text)


def test_validate_collects_every_problem_with_its_path() -> None:
    text = (
        "<Cluster><Name>pt</Name><NumElts>3</NumElts>"
        "<DBL><Name>x</Name><Val>1,0</Val></DBL>"
        "<I8><Name>y</Name><Val>300</Val></I8></Cluster>"
    )
    problems = lvxml.validate(text)
    assert len(problems) == 3
    assert problems[0].startswith("Cluster[pt]: cluster NumElts 3")
    assert problems[1].startswith("Cluster[pt]/DBL[x]: invalid float")
    assert problems[2].startswith("Cluster[pt]/I8[y]: 300 is out of range")


def test_structural_errors_name_their_location() -> None:
    text = (
        "<LVData><Cluster><Name>pt</Name><NumElts>1</NumElts>"
        "<DBL><Name>x</Name><Value>1</Value></DBL></Cluster></LVData>"
    )
    with pytest.raises(lvxml.LVXMLError) as info:
        lvxml.parse(text)
    assert info.value.path == "LVData/Cluster[pt]/DBL[x]"
    assert "expected <Val>, found <Value>" in info.value.message

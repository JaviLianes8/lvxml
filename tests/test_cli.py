"""The command line, run in-process through `main`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import REAL_FILES

from lvxml import __version__
from lvxml._cli import main

REAL = REAL_FILES[0]


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"lvxml {__version__}"


def test_help_lists_commands_and_examples(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    for word in ("to-json", "to-xml", "validate", "examples:", "lvxml to-json --values -"):
        assert word in out


def test_to_json_tree_then_to_xml_is_byte_exact(tmp_path: Path) -> None:
    tree = tmp_path / "tree.json"
    back = tmp_path / "back.xml"
    assert main(["to-json", str(REAL), "-o", str(tree)]) == 0
    assert json.loads(tree.read_text(encoding="utf-8"))["items"][0]["tag"] == "Version"
    assert main(["to-xml", str(tree), "-o", str(back)]) == 0
    assert back.read_bytes() == REAL.read_bytes()


def test_to_json_values(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["to-json", "--values", str(REAL)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [entry["type"] for entry in data] == ["DBL", "DBL", "DBL", "Cluster"]
    assert data[1] == {"name": "Min", "type": "DBL", "value": 0.11250854849828}


def test_to_json_values_writes_complex_as_re_im(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "z.xml"
    source.write_text("<CDB><Name>z</Name><Val>1.5 +-2 i</Val></CDB>", encoding="utf-8")
    assert main(["to-json", "--values", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["value"] == {"re": 1.5, "im": -2.0}


def test_to_xml_lf_newlines(tmp_path: Path) -> None:
    tree = tmp_path / "t.json"
    tree.write_text(
        '{"wrapped": false, "namespace": null, "items": [{"tag": "I8", "name": "n", "val": "1"}]}',
        encoding="utf-8",
    )
    out = tmp_path / "o.xml"
    assert main(["to-xml", "--newline", "lf", str(tree), "-o", str(out)]) == 0
    assert out.read_bytes() == b"<I8>\n<Name>n</Name>\n<Val>1</Val>\n</I8>"


def test_validate_reports_ok_and_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<U8><Name>x</Name><Val>256</Val></U8>", encoding="utf-8")
    assert main(["validate", str(REAL), str(bad)]) == 1
    captured = capsys.readouterr()
    assert f"{REAL}: OK" in captured.out
    assert "out of range for U8" in captured.err
    assert str(bad) not in captured.out


@pytest.mark.parametrize(
    ("argv", "status"),
    [
        (["to-json", "missing-file.xml"], 1),
        (["to-xml", "missing-file.json"], 1),
        (["validate", "missing-file.xml"], 1),
        (["to-json", "--encoding", "no-such-codec", "x.xml"], 2),
        (["frobnicate"], 2),
        ([], 2),
    ],
)
def test_problems_exit_1_and_usage_mistakes_exit_2_on_stderr(
    argv: list[str], status: int, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == status
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err or "missing-file" in captured.err


def test_invalid_json_and_bad_encoding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert main(["to-xml", str(broken)]) == 1
    assert "invalid JSON" in capsys.readouterr().err
    latin = tmp_path / "latin.xml"
    latin.write_bytes("<String><Name>s</Name><Val>caf\xe9</Val></String>".encode("cp1252"))
    assert main(["to-json", "--values", str(latin)]) == 1
    assert "--encoding" in capsys.readouterr().err
    assert main(["to-json", "--values", "--encoding", "cp1252", str(latin)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["value"] == "caf\xe9"

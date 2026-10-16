"""Install the built wheel into a throwaway venv and use it as an outside consumer would."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import ENV, FIXTURES, REAL_FILES

import lvxml

REAL = REAL_FILES[0]
CAPTURE = FIXTURES / "labview2026" / "save-cont-escapes.xml"
CODEPAGE = FIXTURES / "labview2026" / "save-cont-codepage.xml"


def run(command: list[str], stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, input=stdin, capture_output=True, timeout=120, env=ENV)


def test_version_from_the_script_and_from_python_m(installed: tuple[Path, Path]) -> None:
    python, script = installed
    for command in ([str(script)], [str(python), "-m", "lvxml"]):
        result = run([*command, "--version"])
        assert result.returncode == 0
        assert result.stdout.decode().strip() == f"lvxml {lvxml.__version__}"


def test_validate_labview_files(installed: tuple[Path, Path]) -> None:
    _, script = installed
    result = run([str(script), "validate", str(REAL), str(CAPTURE)])
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().splitlines() == [f"{REAL}: OK", f"{CAPTURE}: OK"]


def test_labview_files_through_json_and_back_are_byte_exact(
    installed: tuple[Path, Path], tmp_path: Path
) -> None:
    _, script = installed
    for source, encoding in ((REAL, "utf-8"), (CAPTURE, "utf-8"), (CODEPAGE, "cp1252")):
        tree, back = tmp_path / "tree.json", tmp_path / "back.xml"
        assert (
            run(
                [str(script), "to-json", "--encoding", encoding, str(source), "-o", str(tree)]
            ).returncode
            == 0
        )
        assert (
            run(
                [str(script), "to-xml", "--encoding", encoding, str(tree), "-o", str(back)]
            ).returncode
            == 0
        )
        assert back.read_bytes() == source.read_bytes()


def test_stdout_pipeline_is_byte_exact(installed: tuple[Path, Path]) -> None:
    _, script = installed
    tree = run([str(script), "to-json", "-"], stdin=REAL.read_bytes())
    assert tree.returncode == 0
    back = run([str(script), "to-xml", "-"], stdin=tree.stdout)
    assert back.returncode == 0
    assert back.stdout == REAL.read_bytes()


def test_values_of_the_real_file(installed: tuple[Path, Path]) -> None:
    _, script = installed
    result = run([str(script), "to-json", "--values", str(REAL)])
    assert result.returncode == 0
    graph = json.loads(result.stdout)[3]
    assert graph["name"] == "Random Graph Data"
    assert graph["value"]["Delta X"] == 0.25
    assert len(graph["value"]["Values"]) == 10


def test_problems_exit_1_and_usage_mistakes_exit_2(
    installed: tuple[Path, Path], tmp_path: Path
) -> None:
    _, script = installed
    bad = tmp_path / "bad.xml"
    bad.write_bytes(REAL.read_bytes().replace(b"<NumElts>3</NumElts>", b"<NumElts>4</NumElts>"))
    result = run([str(script), "validate", str(bad)])
    assert (result.returncode, result.stdout) == (1, b"")
    assert b"NumElts 4 does not match 3" in result.stderr
    broken = run([str(script), "to-json", "-"], stdin=b"<DBL><Name>x</Name>")
    assert broken.returncode == 1 and b"invalid XML" in broken.stderr
    assert run([str(script), "frobnicate"]).returncode == 2
    hint = run([str(script), "to-json", str(CODEPAGE)])
    assert hint.returncode == 1 and b"--encoding" in hint.stderr


def test_a_consumer_script_uses_the_public_api(
    installed: tuple[Path, Path], tmp_path: Path
) -> None:
    python, _ = installed
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "import lvxml\n"
        "schema = lvxml.Cluster({'x': 'DBL', 'mode': lvxml.LVEnum(('Idle', 'Run'))})\n"
        "text = lvxml.to_lv_xml({'x': 1.5, 'mode': 'Run'}, schema, name='pt')\n"
        "assert lvxml.from_lv_xml(text) == {'x': 1.5, 'mode': 'Run'}\n"
        "assert lvxml.validate(text) == []\n"
        "print(sorted(lvxml.__all__) == sorted(dir(lvxml)) or 'ok')\n",
        encoding="utf-8",
    )
    result = run([str(python), str(consumer)])
    assert result.returncode == 0, result.stderr

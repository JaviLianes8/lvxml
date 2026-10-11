"""Install the package in editable mode and drive the real `lvxml` console script."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import sysconfig
from importlib import metadata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import pytest
from conftest import REAL_FILES

import lvxml

ROOT = Path(__file__).resolve().parents[1]
REAL = REAL_FILES[0]

pytestmark = pytest.mark.skipif(
    sys.prefix == sys.base_prefix,
    reason="installs the package, so it only runs inside a virtual environment",
)


@pytest.fixture(scope="module")
def script() -> str:
    command = [sys.executable, "-m", "pip", "install", "--no-deps", "--no-build-isolation"]
    subprocess.run([*command, "-e", str(ROOT)], check=True, capture_output=True, timeout=300)
    direct_url = json.loads(metadata.distribution("lvxml").read_text("direct_url.json") or "{}")
    assert direct_url["dir_info"] == {"editable": True}
    assert Path(url2pathname(urlparse(direct_url["url"]).path)).resolve() == ROOT
    found = shutil.which("lvxml", path=sysconfig.get_path("scripts"))
    assert found is not None, "pip did not install the lvxml console script"
    return found


def run(script: str, *args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([script, *args], input=stdin, capture_output=True, timeout=60)


def test_version(script: str) -> None:
    result = run(script, "--version")
    assert result.returncode == 0
    assert result.stdout.decode().strip() == f"lvxml {lvxml.__version__}"


def test_validate_real_file(script: str) -> None:
    result = run(script, "validate", str(REAL))
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == f"{REAL}: OK"


def test_real_file_through_json_and_back_is_byte_exact(script: str, tmp_path: Path) -> None:
    tree, back = tmp_path / "tree.json", tmp_path / "back.xml"
    assert run(script, "to-json", str(REAL), "-o", str(tree)).returncode == 0
    assert run(script, "to-xml", str(tree), "-o", str(back)).returncode == 0
    assert back.read_bytes() == REAL.read_bytes()


def test_stdout_pipeline_is_byte_exact(script: str) -> None:
    tree = run(script, "to-json", "-", stdin=REAL.read_bytes())
    assert tree.returncode == 0
    back = run(script, "to-xml", "-", stdin=tree.stdout)
    assert back.returncode == 0
    assert back.stdout == REAL.read_bytes()


def test_values_of_real_file(script: str) -> None:
    result = run(script, "to-json", "--values", str(REAL))
    assert result.returncode == 0
    data = json.loads(result.stdout)
    graph = data[3]
    assert graph["name"] == "Random Graph Data"
    assert graph["value"]["Delta X"] == 0.25
    assert len(graph["value"]["Values"]) == 10


def test_help_example_runs(script: str) -> None:
    result = run(script, "to-json", "--values", "-", stdin=b"<I32><Name>n</Name><Val>7</Val></I32>")
    assert result.returncode == 0
    assert json.loads(result.stdout) == [{"name": "n", "type": "I32", "value": 7}]


def test_errors_exit_1_on_stderr(script: str, tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_bytes(REAL.read_bytes().replace(b"<NumElts>3</NumElts>", b"<NumElts>4</NumElts>"))
    result = run(script, "validate", str(bad))
    assert result.returncode == 1
    assert result.stdout == b""
    assert b"NumElts 4 does not match 3" in result.stderr
    broken = run(script, "to-json", "-", stdin=b"<DBL><Name>x</Name>")
    assert broken.returncode == 1
    assert b"invalid XML" in broken.stderr

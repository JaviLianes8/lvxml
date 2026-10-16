"""Shared paths to the ground-truth fixtures, and a throwaway venv with the built wheel.

``LVXML_WHEEL`` names a wheel to install; otherwise one is built from this source tree. The
venv shares nothing with the test runner, so the end-to-end tests drive the real package.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
# NI's schema is not tracked: scripts/capture_ni.py copies it from a LabVIEW install.
XSD = FIXTURES / "ni" / "LVXMLSchema.xsd"
# Written by LabVIEW 2026 itself (see README, "Test fixtures").
REAL_FILES = sorted((FIXTURES / "real").glob("*.xml"))
# Hand-written from LVXMLSchema.xsd to cover every element it defines.
SCHEMA_FILES = sorted((FIXTURES / "schema").glob("*.xml"))
_LEAKY = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP")
ENV = {key: value for key, value in os.environ.items() if key.upper() not in _LEAKY}


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    given = os.environ.get("LVXML_WHEEL")
    if given:
        return Path(given)
    if not (ROOT / "src" / "lvxml" / "__init__.py").is_file():
        pytest.skip("no source tree to build from; set LVXML_WHEEL to a built wheel")
    wheels = tmp_path_factory.mktemp("wheels")
    build = [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps"]
    if importlib.util.find_spec("hatchling") is not None:
        build.append("--no-build-isolation")
    subprocess.run([*build, "-w", str(wheels), str(ROOT)], check=True, timeout=600, env=ENV)
    (wheel,) = wheels.glob("lvxml-*.whl")
    return wheel


@pytest.fixture(scope="session")
def installed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """The throwaway venv's Python and its ``lvxml`` console script."""
    wheel = _wheel(tmp_path_factory)
    with zipfile.ZipFile(wheel) as archive:
        assert "lvxml/__init__.py" in archive.namelist(), "the wheel holds no package"
    env_dir = tmp_path_factory.mktemp("venv")
    venv.EnvBuilder(with_pip=True).create(env_dir)
    scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    install = [str(python), "-m", "pip", "install", "--quiet", "--no-index", "--no-deps"]
    subprocess.run([*install, str(wheel)], check=True, timeout=600, env=ENV)
    where = [str(python), "-c", "import lvxml; print(lvxml.__file__)"]
    location = subprocess.run(
        where, check=True, capture_output=True, text=True, cwd=env_dir, env=ENV
    )
    assert Path(location.stdout.strip()).resolve().is_relative_to(env_dir.resolve())
    found = shutil.which("lvxml", path=str(scripts))
    assert found is not None, "pip did not install the lvxml console script"
    return python, Path(found)

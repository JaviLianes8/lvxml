"""The NI schema manifest is valid and the script that restores the schema follows it."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from conftest import FIXTURES, ROOT

MANIFEST = FIXTURES / "ni" / "MANIFEST.json"


def _capture_ni() -> object:
    spec = importlib.util.spec_from_file_location("capture_ni", ROOT / "scripts" / "capture_ni.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_manifest_is_json_with_every_field() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry = entries["LVXMLSchema.xsd"]
    assert {"title", "origin", "labview", "licence", "retrieved", "size", "sha256"} <= set(entry)
    assert entry["size"] == 21250 and len(entry["sha256"]) == 64
    assert entry["origin"].endswith("vi.lib/Utility/LVXMLSchema.xsd")


def test_the_restore_script_refuses_a_file_that_differs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = tmp_path / "LVXMLSchema.xsd"
    fake.write_bytes(b"<xsd:schema/>")
    before = sorted(p.name for p in MANIFEST.parent.iterdir())
    assert _capture_ni().main([str(fake)]) == 1  # type: ignore[attr-defined]
    assert "manifest differs" in capsys.readouterr().out
    assert sorted(p.name for p in MANIFEST.parent.iterdir()) == before


@pytest.mark.skipif(not (FIXTURES / "ni" / "LVXMLSchema.xsd").is_file(), reason="schema absent")
def test_the_restore_script_accepts_the_real_schema() -> None:
    xsd = FIXTURES / "ni" / "LVXMLSchema.xsd"
    assert _capture_ni().main([str(xsd)]) == 0  # type: ignore[attr-defined]

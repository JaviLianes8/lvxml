import importlib.resources
import re
from pathlib import Path

import lvxml

# The public API. This list is the contract and the tests below fail if the module
# and this list disagree.
PUBLIC_API: list[str] = [
    "LVDATA_NAMESPACE",
    "Array",
    "Cluster",
    "Document",
    "LVEnum",
    "LVXMLError",
    "Node",
    "dump",
    "from_lv_xml",
    "from_lv_xml_all",
    "parse",
    "to_lv_xml",
    "to_node",
    "to_value",
    "validate",
]

ROOT = Path(__file__).resolve().parents[1]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvxml.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvxml.__all__:
        assert hasattr(lvxml, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvxml.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert match.group(1) == lvxml.__version__


def test_console_script_points_at_the_cli_main() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'lvxml = "lvxml._cli:main"' in text


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvxml").joinpath("py.typed").is_file()


def test_every_source_file_stays_within_200_lines() -> None:
    for path in (ROOT / "src" / "lvxml").glob("*.py"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path.name

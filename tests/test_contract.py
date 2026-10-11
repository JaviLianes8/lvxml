import importlib.resources

import lvxml

# The public API. This list is the contract and the tests below fail if the module
# and this list disagree.
PUBLIC_API: list[str] = ["Array", "Cluster", "LVXMLError", "from_lv_xml", "to_lv_xml"]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvxml.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvxml.__all__:
        assert hasattr(lvxml, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvxml.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvxml").joinpath("py.typed").is_file()

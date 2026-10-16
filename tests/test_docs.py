"""The documentation is executable: doctests, README and GUIDE examples, CLI transcripts."""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil
import re
import shlex
import typing
from pathlib import Path

import pytest

import lvxml
from lvxml._cli import main

_ROOT = Path(__file__).resolve().parents[1]
_MODULES = ["lvxml"] + [
    f"lvxml.{m.name}" for m in pkgutil.iter_modules(lvxml.__path__) if m.name != "__main__"
]
_CALLABLES = [n for n in lvxml.__all__ if callable(getattr(lvxml, n))]


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0


@pytest.mark.parametrize("name", lvxml.__all__)
def test_every_public_name_has_a_docstring_with_an_example(name: str) -> None:
    if name == "LVDATA_NAMESPACE":
        assert "lvxml.LVDATA_NAMESPACE" in (lvxml.__doc__ or "")
        return
    assert ">>>" in (getattr(lvxml, name).__doc__ or ""), name


def test_the_doctests_cover_every_public_name() -> None:
    finder = doctest.DocTestFinder()
    examples = "".join(
        example.source
        for module in _MODULES
        for test in finder.find(importlib.import_module(module))
        for example in test.examples
    )
    for name in lvxml.__all__:
        assert re.search(rf"\b{name}\b", examples), name


@pytest.mark.parametrize("name", _CALLABLES)
def test_type_hints_resolve_at_run_time(name: str) -> None:
    target = getattr(lvxml, name)
    typing.get_type_hints(target)
    for member in vars(target).values() if inspect.isclass(target) else []:
        function = getattr(member, "__func__", member)
        if inspect.isfunction(function):
            typing.get_type_hints(function)


def _run_pycon(name: str) -> int:
    text = (_ROOT / name).read_text(encoding="utf-8")
    blocks = re.findall(r"```pycon\n(.*?)```", text, re.S)
    assert blocks, name
    parser, runner = doctest.DocTestParser(), doctest.DocTestRunner()
    session: dict[str, object] = {}
    for number, block in enumerate(blocks):
        test = parser.get_doctest(block, session, f"{name}[{number}]", name, 0)
        runner.run(test, clear_globs=False)
        session.update(test.globs)
    assert runner.summarize(verbose=False).failed == 0
    return len(blocks)


def test_readme_examples_run_and_print_what_they_show() -> None:
    assert _run_pycon("README.md") >= 2


def test_guide_examples_run_and_print_what_they_show() -> None:
    assert _run_pycon("GUIDE.md") >= 7


def _transcripts() -> list[tuple[list[str], list[str]]]:
    runs: list[tuple[list[str], list[str]]] = []
    text = (_ROOT / "GUIDE.md").read_text(encoding="utf-8")
    for block in re.findall(r"```console\n(.*?)```", text, re.S):
        for line in block.splitlines():
            if line.startswith("$ lvxml "):
                runs.append((shlex.split(line, posix=True)[2:], []))
            else:
                runs[-1][1].append(line)
    return runs


@pytest.mark.parametrize(("args", "expected"), _transcripts())
def test_guide_transcripts_match(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    expected: list[str],
) -> None:
    monkeypatch.chdir(_ROOT)
    status = main(args)
    captured = capsys.readouterr()
    assert (captured.out + captured.err).splitlines() == expected
    assert status == (1 if captured.err else 0)

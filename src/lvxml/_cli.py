"""The `lvxml` command: convert LabVIEW XML to and from JSON, and validate it."""

from __future__ import annotations

import argparse
import codecs
import json
import math
import sys
from collections.abc import Sequence
from typing import NoReturn

from . import __version__
from ._checks import document_problems, validate
from ._decode import to_value
from ._dump import dump
from ._errors import LVXMLError
from ._node import Document
from ._numbers import format_float
from ._parse import parse

EXAMPLES = """\
examples:
  echo "<I32><Name>n</Name><Val>7</Val></I32>" | lvxml to-json --values -
  lvxml to-json data.xml -o data.json      lossless tree, every name and raw value kept
  lvxml to-json --values data.xml          plain values: numbers, strings, lists, dicts
  lvxml to-xml data.json -o data.xml       tree JSON back to LabVIEW XML
  lvxml validate data.xml other.xml        check shape and values, exit 1 on any problem

A FILE of "-" reads standard input. Errors go to standard error with exit status 1.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="lvxml",
        description="Read, write and check LabVIEW Flatten To XML data.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvxml {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    to_json = commands.add_parser("to-json", help="convert LabVIEW XML to JSON")
    to_json.add_argument("file", metavar="FILE", help="LabVIEW XML file, or - for stdin")
    to_json.add_argument("--values", action="store_true", help="emit plain values, not the tree")
    to_xml = commands.add_parser("to-xml", help="convert tree JSON (from to-json) to LabVIEW XML")
    to_xml.add_argument("file", metavar="FILE", help="tree JSON file, or - for stdin")
    to_xml.add_argument(
        "--newline", choices=["crlf", "lf"], default="crlf", help="line break (default: crlf)"
    )
    check = commands.add_parser("validate", help="check LabVIEW XML files")
    check.add_argument("files", metavar="FILE", nargs="+", help="LabVIEW XML files")
    for sub in (to_json, to_xml, check):
        sub.add_argument(
            "--encoding", default="utf-8", help="text encoding of files (default: utf-8)"
        )
    for sub in (to_json, to_xml):
        sub.add_argument("-o", "--output", metavar="OUT", help="write here instead of stdout")
    return parser


def _read(path: str, encoding: str) -> str:
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as handle:
            data = handle.read()
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        where = "stdin" if path == "-" else path
        raise LVXMLError(f"{where} is not valid {encoding} ({exc.reason}); try --encoding") from exc


def _write(text: str, output: str | None, encoding: str) -> None:
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError as exc:
        bad = exc.object[exc.start : exc.end]
        raise LVXMLError(f"{bad!r} cannot be written as {encoding}; try --encoding utf-8") from exc
    if output is None:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    else:
        with open(output, "wb") as handle:
            handle.write(data)


def _plain(value: object) -> object:
    """Make a value strict JSON: complex as {"re", "im"}, NaN and Inf as strings."""
    if isinstance(value, float) and not math.isfinite(value):
        return format_float(value, "DBL")
    if isinstance(value, complex):
        return {"re": _plain(value.real), "im": _plain(value.imag)}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _to_json(args: argparse.Namespace) -> int:
    document = parse(_read(args.file, args.encoding))
    if args.values:
        found = document_problems(document)
        if found:
            raise LVXMLError(found[0])
        data: object = [
            {"name": node.name, "type": node.tag, "value": _plain(to_value(node))}
            for node in document.values
        ]
    else:
        data = document.to_dict()
    text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    _write(text, args.output, "utf-8")
    return 0


def _to_xml(args: argparse.Namespace) -> int:
    try:
        data = json.loads(_read(args.file, args.encoding))
    except json.JSONDecodeError as exc:
        raise LVXMLError(f"invalid JSON: {exc}") from exc
    newline = "\r\n" if args.newline == "crlf" else "\n"
    _write(dump(Document.from_dict(data), newline=newline), args.output, args.encoding)
    return 0


def _validate(args: argparse.Namespace) -> int:
    status = 0
    for path in args.files:
        try:
            found = validate(_read(path, args.encoding))
        except (LVXMLError, OSError) as exc:
            found = [str(exc)]
        for problem in found:
            print(f"{path}: {problem}", file=sys.stderr)
        if found:
            status = 1
        else:
            print(f"{path}: OK")
    return status


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with `argv` (default: ``sys.argv[1:]``); return the exit status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        codecs.lookup(args.encoding)
    except LookupError:
        parser.error(f"unknown encoding {args.encoding!r}")
    handlers = {"to-json": _to_json, "to-xml": _to_xml, "validate": _validate}
    try:
        return handlers[args.command](args)
    except (LVXMLError, OSError) as exc:
        print(f"lvxml: error: {exc}", file=sys.stderr)
        return 1
    except RecursionError:
        print("lvxml: error: the input is nested too deeply", file=sys.stderr)
        return 1

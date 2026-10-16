"""Seeded fuzzing: no crash outside the documented errors, no hang, no quadratic blow-up."""

from __future__ import annotations

import contextlib
import math
import random
import time
from collections.abc import Callable

import pytest
from conftest import FIXTURES, REAL_FILES, SCHEMA_FILES

from lvxml import (
    Array,
    Cluster,
    LVEnum,
    LVXMLError,
    dump,
    from_lv_xml_all,
    parse,
    to_node,
    to_value,
    validate,
)
from lvxml._schema import Schema, Value

SEEDS = [b.read_bytes() for b in [*REAL_FILES, *SCHEMA_FILES]]
SEEDS += [p.read_bytes() for p in sorted((FIXTURES / "labview2026").glob("save-*.xml"))]
ALPHABET = b"<>/&;#x\r\n\t \x00\x07\xe9NameValDimsizeNumEltsChoiceClusterArrayDBLI8LVData"


def mutate(rng: random.Random, data: bytes) -> bytes:
    out = bytearray(data)
    for _ in range(rng.randint(1, 8)):
        where = rng.randrange(len(out) + 1)
        action = rng.randrange(4)
        if action == 0 and out:
            del out[where : where + rng.randint(1, 20)]
        elif action == 1:
            out[where:where] = bytes(rng.choice(ALPHABET) for _ in range(rng.randint(1, 6)))
        elif action == 2 and out:
            start = rng.randrange(len(out))
            out[where:where] = out[start : start + rng.randint(1, 60)]
        elif out:
            out[min(where, len(out) - 1)] = rng.randrange(256)
    return bytes(out)


@pytest.mark.parametrize("seed", range(4))
def test_mutated_files_only_raise_lvxml_error(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(1500):
        data = mutate(rng, rng.choice(SEEDS))
        for text in (data, data.decode("cp1252", "replace")):
            assert isinstance(validate(text), list)
            try:
                document = parse(text)
                from_lv_xml_all(text)
            except LVXMLError:
                continue
            assert parse(dump(document)) == document


TAGS = ["I8", "I64", "U16", "U64", "SGL", "DBL", "EXT", "CDB", "Boolean", "String", "Path"]


def random_schema(rng: random.Random, depth: int = 0) -> Schema:
    kind = rng.randrange(6 if depth < 3 else 2)
    if kind <= 1:
        return rng.choice(TAGS)
    if kind == 2:
        return LVEnum(tuple(f"c{i}" for i in range(rng.randint(1, 4))), rng.choice(["EB", "EW"]))
    if kind == 3:
        element = random_schema(rng, depth + 1)
        return Array(Cluster({"e": element}) if isinstance(element, Array) else element, 2)
    if kind == 4:
        return Array(rng.choice(TAGS))
    return Cluster({f"f{i}": random_schema(rng, depth + 1) for i in range(rng.randint(0, 3))})


def random_text(rng: random.Random) -> str:
    return "".join(rng.choice("ab &<>\"'\r\n\t\x01\x1f\u00e9\ue000\ue020") for _ in range(6))


def random_value(rng: random.Random, schema: Schema) -> Value:
    if isinstance(schema, LVEnum):
        return rng.choice(schema.choices)
    if isinstance(schema, Cluster):
        return {name: random_value(rng, sub) for name, sub in schema.fields.items()}
    if isinstance(schema, Array):
        rows: list[Value] = [
            [random_value(rng, schema.element) for _ in range(2)] for _ in range(2)
        ]
        return rows if schema.ndim == 2 else rows[0]
    numbers: dict[str, Callable[[], Value]] = {
        "I8": lambda: rng.randint(-128, 127),
        "I64": lambda: rng.randint(-(2**63), 2**63 - 1),
        "U16": lambda: rng.randint(0, 65535),
        "U64": lambda: rng.randint(0, 2**64 - 1),
        "SGL": lambda: rng.choice([0.5, -2.25, math.inf]),
        "DBL": lambda: rng.choice([rng.uniform(-1e300, 1e300), 5e-324, -0.0, math.nan]),
        "EXT": lambda: rng.uniform(-1, 1),
        "CDB": lambda: complex(rng.uniform(-9, 9), rng.choice([1.5, -math.inf])),
        "Boolean": lambda: rng.random() < 0.5,
    }
    assert isinstance(schema, str)
    return numbers[schema]() if schema in numbers else random_text(rng)


def same(a: object, b: object) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return (math.isnan(a) and math.isnan(b)) or (
            a == b and math.copysign(1, a) == math.copysign(1, b)
        )
    if isinstance(a, complex) and isinstance(b, complex):
        return same(a.real, b.real) and same(a.imag, b.imag)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


@pytest.mark.parametrize("seed", range(3))
def test_random_values_round_trip_through_text(seed: int) -> None:
    rng = random.Random(1000 + seed)
    for _ in range(400):
        schema = random_schema(rng)
        value = random_value(rng, schema)
        node = to_node(value, schema, name=random_text(rng))
        for newline in ("\r\n", "\n"):
            (back,) = parse(dump(node, newline=newline)).values
            assert back == node
            assert same(to_value(back), value)


def timed(make: Callable[[int], str], run: Callable[[str], object]) -> list[float]:
    times = []
    for size in (20_000, 80_000):
        text = make(size)
        start = time.perf_counter()
        with contextlib.suppress(LVXMLError):
            run(text)
        times.append(time.perf_counter() - start)
    return times


SHAPES: dict[str, Callable[[int], str]] = {
    "values": lambda n: "<LVData>" + "<I8><Name>a</Name><Val>1</Val></I8>" * (n // 8) + "</LVData>",
    "long text": lambda n: f"<String><Name>s</Name><Val>{'a&amp;&quot;' * n}</Val></String>",
    "ampersands": lambda n: f"<String><Name>s</Name><Val>{'& ' * n}</Val></String>",
    "controls": lambda n: f"<String><Name>s</Name><Val>{chr(7) * n}\r</Val></String>",
    "carriage returns": lambda n: (
        f"<String><Name>s</Name><Val>{'a' * 5}{chr(13) * n}</Val></String>"
    ),
    "array": lambda n: (
        "<Array><Name>a</Name><Dimsize>"
        + str(n // 8)
        + "</Dimsize>"
        + "<U8><Name></Name><Val>1</Val></U8>" * (n // 8)
        + "</Array>"
    ),
    "markup": lambda n: "<" * n,
    "deep": lambda n: "<Cluster><Name>c</Name><NumElts>1</NumElts>" * (n // 40) + "x",
}


@pytest.mark.parametrize("shape", SHAPES)
def test_work_grows_linearly_with_input(shape: str) -> None:
    def run(text: str) -> object:
        return (validate(text), from_lv_xml_all(text))

    small, large = min(timed(SHAPES[shape], run) for _ in range(3))
    assert large < max(small, 0.002) * 4 * 3, (shape, small, large)

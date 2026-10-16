"""LabVIEW type tags from LVXMLSchema.xsd and the schema that pins Python values to them."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ._text import quote

FLOAT_TAGS: frozenset[str] = frozenset({"SGL", "DBL", "EXT"})
COMPLEX_TAGS: frozenset[str] = frozenset({"CSG", "CDB", "CXT"})

INT_RANGES: dict[str, tuple[int, int]] = {
    "I8": (-(2**7), 2**7 - 1),
    "I16": (-(2**15), 2**15 - 1),
    "I32": (-(2**31), 2**31 - 1),
    "I64": (-(2**63), 2**63 - 1),
    "U8": (0, 2**8 - 1),
    "U16": (0, 2**16 - 1),
    "U32": (0, 2**32 - 1),
    "U64": (0, 2**64 - 1),
}

# Enum tags carry their value as an index into the <Choice> list, sized like U8/U16/U32.
ENUM_RANGES: dict[str, tuple[int, int]] = {
    "EB": INT_RANGES["U8"],
    "EW": INT_RANGES["U16"],
    "EL": INT_RANGES["U32"],
}

# Types whose payload is free text in <Val>.
TEXT_TAGS: frozenset[str] = frozenset({"String", "Path", "DAQChannel"})

# Types built on the schema's LVDataType: exactly <Name> then <Val>.
SIMPLE_TAGS: frozenset[str] = (
    FLOAT_TAGS | COMPLEX_TAGS | frozenset(INT_RANGES) | TEXT_TAGS | {"Boolean"}
)

_WAVEFORM_BASES: tuple[str, ...] = ("DBL", "I16", "SGL", "EXT", "I8", "I32", "I64")
_WAVEFORM_BASES += ("U8", "U16", "U32", "U64", "CSG", "CDB", "CXT")

# Types the schema defines as <Name> followed by any number of <Cluster> elements.
CLUSTERED_TAGS: frozenset[str] = frozenset(
    {"WDT", "DynamicData", "Timestamp", "DigitalData", "DigitalWaveform"}
    | {f"{base}Waveform" for base in _WAVEFORM_BASES}
)

# Every value element allowed inside <LVData>, <Cluster> and <LvVariant>.
VALUE_TAGS: frozenset[str] = (
    SIMPLE_TAGS
    | frozenset(ENUM_RANGES)
    | CLUSTERED_TAGS
    | {"Refnum", "Cluster", "Array", "LvVariant"}
)

# The schema does not allow an <Array> directly inside an <Array>.
ARRAY_ITEM_TAGS: frozenset[str] = VALUE_TAGS - {"Array"}

# Tags `to_lv_xml` accepts as a plain string schema.
SCALAR_TAGS: frozenset[str] = SIMPLE_TAGS


@dataclass(frozen=True)
class Array:
    """A LabVIEW array of homogeneous `element` values with `ndim` dimensions.

    A one-dimensional array maps to a list, a two-dimensional one to a list of equal
    length lists, and so on, in LabVIEW's row-major order. LabVIEW has no array of
    arrays, so `element` cannot be an `Array`.

    >>> Array("I32", ndim=2)
    Array(element='I32', ndim=2)
    """

    element: Schema
    ndim: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.ndim, bool) or not isinstance(self.ndim, int):
            raise TypeError(f"Array ndim must be an int, got {type(self.ndim).__name__}")
        if self.ndim < 1:
            raise ValueError(f"Array ndim must be at least 1, got {self.ndim}")
        if isinstance(self.element, Array):
            raise ValueError("an Array element cannot be an Array; wrap it in a Cluster")
        check_schema(self.element)


@dataclass(frozen=True)
class Cluster:
    """A LabVIEW cluster: named fields kept in declaration order.

    `fields` maps each field name to its schema; it is copied into a new dict.

    >>> Cluster({"x": "DBL", "on": "Boolean"}).fields
    {'x': 'DBL', 'on': 'Boolean'}
    """

    fields: dict[str, Schema]

    def __post_init__(self) -> None:
        if not isinstance(self.fields, Mapping):
            raise TypeError(f"Cluster fields must be a mapping, got {type(self.fields).__name__}")
        fields = dict(self.fields)
        for name, schema in fields.items():
            if not isinstance(name, str):
                raise TypeError(f"a Cluster field name must be a str, got {type(name).__name__}")
            check_schema(schema)
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True)
class LVEnum:
    """A LabVIEW enum: its ordered `choices` and the `EB`, `EW` or `EL` storage tag.

    Values are written as the index of a choice; a Python value may be the choice label
    or its integer index. `EW` (16-bit) is LabVIEW's default enum representation.

    >>> LVEnum(["Idle", "Run"])
    LVEnum(choices=('Idle', 'Run'), tag='EW')
    """

    choices: tuple[str, ...]
    tag: str = "EW"

    def __post_init__(self) -> None:
        if isinstance(self.choices, (str, bytes)) or not isinstance(self.choices, Iterable):
            raise TypeError("LVEnum choices must be a sequence of str labels, not one str")
        choices = tuple(self.choices)
        if not all(isinstance(c, str) for c in choices):
            raise TypeError("LVEnum choices must be a sequence of str labels")
        object.__setattr__(self, "choices", choices)
        if not isinstance(self.tag, str):
            raise TypeError(f"LVEnum tag must be a str, got {type(self.tag).__name__}")
        if self.tag not in ENUM_RANGES:
            raise ValueError(f"LVEnum tag must be EB, EW or EL, got {quote(self.tag)}")
        if not choices:
            raise ValueError("LVEnum needs at least one choice")
        if len(set(choices)) != len(choices):
            raise ValueError("LVEnum choices must be unique")
        if len(choices) > ENUM_RANGES[self.tag][1] + 1:
            raise ValueError(f"too many choices for {self.tag}")


def check_schema(schema: object) -> None:
    """Raise unless `schema` is a scalar tag string or a built schema object."""
    if isinstance(schema, (Array, Cluster, LVEnum)):
        return
    if not isinstance(schema, str):
        kind = type(schema).__name__
        raise TypeError(f"a schema is a tag string, Array, Cluster or LVEnum, not {kind}")
    if schema not in SCALAR_TAGS:
        raise ValueError(f"unknown scalar tag {quote(schema)}")


for _public in (Array, Cluster, LVEnum):
    _public.__module__ = "lvxml"


# A scalar tag such as "DBL", or a compound container.
Schema = str | Array | Cluster | LVEnum

# Any value this codec maps to Python. bool precedes int because bool is an int subclass.
Value = bool | int | float | complex | str | list["Value"] | dict[str, "Value"]

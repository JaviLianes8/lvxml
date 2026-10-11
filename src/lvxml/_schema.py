"""LabVIEW type tags from LVXMLSchema.xsd and the schema that pins Python values to them."""

from __future__ import annotations

from dataclasses import dataclass

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
    length lists, and so on, in LabVIEW's row-major order.
    """

    element: Schema
    ndim: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.ndim, bool) or not isinstance(self.ndim, int) or self.ndim < 1:
            raise ValueError(f"Array ndim must be a positive int, got {self.ndim!r}")
        if isinstance(self.element, Array):
            raise ValueError("an Array element cannot be an Array; wrap it in a Cluster")


@dataclass(frozen=True)
class Cluster:
    """A LabVIEW cluster: named fields kept in declaration order."""

    fields: dict[str, Schema]


@dataclass(frozen=True)
class LVEnum:
    """A LabVIEW enum: its ordered `choices` and the `EB`, `EW` or `EL` storage tag.

    Values are written as the index of a choice; a Python value may be the choice label
    or its integer index. `EW` (16-bit) is LabVIEW's default enum representation.
    """

    choices: tuple[str, ...]
    tag: str = "EW"

    def __post_init__(self) -> None:
        if isinstance(self.choices, str) or not all(isinstance(c, str) for c in self.choices):
            raise TypeError("LVEnum choices must be a sequence of str labels, not one str")
        object.__setattr__(self, "choices", tuple(self.choices))
        if self.tag not in ENUM_RANGES:
            raise ValueError(f"LVEnum tag must be EB, EW or EL, got {self.tag!r}")
        if not self.choices:
            raise ValueError("LVEnum needs at least one choice")
        if len(set(self.choices)) != len(self.choices):
            raise ValueError("LVEnum choices must be unique")
        if len(self.choices) > ENUM_RANGES[self.tag][1] + 1:
            raise ValueError(f"too many choices for {self.tag}")


# A scalar tag such as "DBL", or a compound container.
Schema = str | Array | Cluster | LVEnum

# Any value this codec maps to Python. bool precedes int because bool is an int subclass.
Value = bool | int | float | complex | str | list["Value"] | dict[str, "Value"]

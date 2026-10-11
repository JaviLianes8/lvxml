"""The type schema that pins each Python value to a LabVIEW datatype tag."""

from __future__ import annotations

from dataclasses import dataclass

FLOAT_TAGS: frozenset[str] = frozenset({"DBL", "SGL"})

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

SCALAR_TAGS: frozenset[str] = FLOAT_TAGS | frozenset(INT_RANGES) | {"Boolean", "String"}


@dataclass(frozen=True)
class Array:
    """A one-dimensional LabVIEW array of homogeneous `element` values."""

    element: Schema


@dataclass(frozen=True)
class Cluster:
    """A LabVIEW cluster: named fields kept in declaration order."""

    fields: dict[str, Schema]


# A scalar tag such as "DBL", or a compound container.
Schema = str | Array | Cluster

# Any value this codec round-trips. bool precedes int because bool is an int subclass.
Value = bool | int | float | str | list["Value"] | dict[str, "Value"]

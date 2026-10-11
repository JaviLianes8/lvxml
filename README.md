# lvxml

Codec for LabVIEW Flatten To XML / Unflatten From XML between its fixed schema and native Python values

## Install

```
pip install lvxml
```

## Usage

LabVIEW's Flatten To XML emits a fixed shape: each value is an element named after its
datatype (`DBL`, `I32`, `Boolean`, `String`, `Array`, `Cluster`), carrying a `<Name>` and
either a `<Val>` or, for containers, a `<Dimsize>` or `<NumElts>` and child elements.

Read LabVIEW XML into plain Python:

```python
from lvxml import from_lv_xml

from_lv_xml("<I32><Name>count</Name><Val>-7</Val></I32>")
# -7

from_lv_xml(
    "<Cluster><Name>pt</Name><NumElts>2</NumElts>"
    "<DBL><Name>x</Name><Val>1.0</Val></DBL>"
    "<I32><Name>y</Name><Val>5</Val></I32></Cluster>"
)
# {"x": 1.0, "y": 5}
```

Write Python back out as XML that Unflatten From XML ingests. A schema names the LabVIEW
type for each value, since a Python `int` could be any width and a `list` any element type:

```python
from lvxml import Array, Cluster, to_lv_xml

to_lv_xml([1.0, 2.5], Array("DBL"), name="xs")

to_lv_xml(
    {"x": 1.5, "flag": True},
    Cluster({"x": "DBL", "flag": "Boolean"}),
    name="pt",
)
```

A scalar schema is a tag string: `"DBL"`, `"SGL"`, `"I8"`, `"I16"`, `"I32"`, `"I64"`,
`"U8"`, `"U16"`, `"U32"`, `"U64"`, `"Boolean"` or `"String"`. `Array(element)` wraps a
one-dimensional array, `Cluster(fields)` an ordered mapping of field name to schema.

Decimals always use a period, regardless of locale, matching what LabVIEW accepts.
Malformed XML, an unknown type tag, an out-of-range integer or a value that does not match
its schema raises `LVXMLError`.

## Covered subset

This handles the common Flatten To XML datatypes: the numeric scalars above, `Boolean`,
`String`, one-dimensional `Array` (including the empty-array `Dimsize` 0 form) and
`Cluster`, nested freely. An `<LVData>` file wrapper with a `<Version>` header is unwrapped
on read.

Out of scope for now, each raising or simply unhandled: multi-dimensional arrays, the
extended-precision `EXT` and complex (`CDB`/`CSG`/`CXT`) numerics, fixed-point `FXP`,
`Variant`, waveforms, paths, enums, timestamps, and the non-finite `NaN`/`Inf` spellings.

## Why

LabVIEW's Flatten To XML and Unflatten From XML use one fixed schema
(`LVXMLSchema.xsd`): datatype-named elements, `Name`-ordered fields, a period decimal
separator independent of locale. LabVIEW produces and reads this schema natively, and NI's
community GXML library also converts data to and from XML, but both run inside LabVIEW and
ship no Python reader. On the Python side, with no LabVIEW running, a generic XML library
parses the tree but knows nothing of that convention, so turning it into usable Python, or
producing XML LabVIEW will accept, is left to hand-written glue every time. Existing LabVIEW
Python packages (pylabview, lvkit, autolv) parse VI source files, not this flattened data
format, and no package on PyPI covers it. `lvxml` is a small, typed, zero-dependency codec
for the common types.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

# lvxml

Codec for LabVIEW Flatten To XML / Unflatten From XML between its fixed schema and native
Python values. Typed, zero dependencies, Python 3.10+.

## Install

```
pip install lvxml
```

## Read LabVIEW XML as Python values

LabVIEW's Flatten To XML emits a fixed shape: each value is an element named after its
datatype (`DBL`, `I32`, `Boolean`, `String`, `Array`, `Cluster`, ...), carrying a `<Name>`
and either a `<Val>` or, for containers, `<Dimsize>` or `<NumElts>` and child elements.

```python
from lvxml import from_lv_xml, from_lv_xml_all

from_lv_xml("<I32><Name>count</Name><Val>-7</Val></I32>")
# -7

from_lv_xml(
    "<Cluster><Name>pt</Name><NumElts>2</NumElts>"
    "<DBL><Name>x</Name><Val>1.0</Val></DBL>"
    "<I32><Name>y</Name><Val>5</Val></I32></Cluster>"
)
# {'x': 1.0, 'y': 5}

with open("Example Flattened XML File.xml", encoding="utf-8") as f:
    from_lv_xml_all(f.read())  # every value in an <LVData> file, Version header skipped
```

| LabVIEW element | Python value |
| --- | --- |
| `I8` `I16` `I32` `I64` `U8` `U16` `U32` `U64` | `int`, range checked |
| `SGL` `DBL` `EXT` | `float` (`NaN`, `Inf`, `-Inf` accepted) |
| `CSG` `CDB` `CXT` | `complex`, from `re +im i` text |
| `Boolean` | `bool` (`1`/`0`, also `true`/`false`) |
| `String` `Path` `DAQChannel` | `str` |
| `EB` `EW` `EL` enums | the selected `<Choice>` label |
| `Refnum` | its `<Val>` text |
| `Array` | `list`, nested once per `<Dimsize>`, row-major |
| `Cluster` | `dict` keyed by field name, in order |
| `LvVariant`, `Timestamp`, `WDT`, `DynamicData`, `DigitalData`, waveforms | `list` of their items' values |

A cluster whose fields share a name (LabVIEW allows unnamed fields) cannot become a dict
without losing data, so it raises; read it through the typed tree below instead.

## Write Python values as LabVIEW XML

A schema names the LabVIEW type of each value, since a Python `int` could be any width
and a `list` any element type:

```python
from lvxml import Array, Cluster, LVEnum, to_lv_xml

to_lv_xml([1.0, 2.5], Array("DBL"), name="xs")
to_lv_xml([[1, 2], [3, 4]], Array("I32", ndim=2), name="grid")
to_lv_xml(
    {"x": 1.5, "flag": True, "mode": "Run", "z": 1 - 2j},
    Cluster({"x": "DBL", "flag": "Boolean", "mode": LVEnum(("Idle", "Run")), "z": "CDB"}),
    name="pt",
)
```

A scalar schema is a tag string: any integer, float or complex tag above, `"Boolean"`,
`"String"`, `"Path"` or `"DAQChannel"`. `Array(element, ndim=1)` is an array (LabVIEW has
no array of arrays, so `element` cannot be an `Array`), `Cluster(fields)` an ordered
mapping of field name to schema, and `LVEnum(choices, tag="EW")` an enum whose value may
be given as a label or an index. An empty array is written with `Dimsize` 0 and one
default element, so the element type stays visible. `to_node` builds the typed tree
instead of text.

## The typed tree: lossless read and write

`parse` keeps everything: names, the raw `<Val>` text, enum choices, `Dimsize`,
`NumElts`, refnum fields and the `<Version>` header. `dump` writes it back in the layout
LabVIEW's file writer uses (one element per line, CRLF, no indentation), so a file
LabVIEW wrote comes back byte for byte.

```python
from lvxml import dump, parse, to_value

with open("Example Flattened XML File.xml", encoding="utf-8", newline="") as f:
    text = f.read()  # newline="" keeps LabVIEW's CRLF line breaks

document = parse(text)
document.version  # '26.3.1f1'
node = document.values[3]  # Node(tag='Cluster', name='Random Graph Data', num_elts=3, ...)
to_value(node)  # the plain Python value
assert dump(document) == text
document.to_dict()  # JSON-ready; Document.from_dict() reverses it
```

`dump(tree, newline="\r\n", indent="", declaration=None)` also writes a single `Node`
bare, the way Flatten To XML returns it, and refuses a node the schema cannot express.

## Validate

`validate(text)` returns a list of problems, empty when the document is good. It first
checks the element structure `LVXMLSchema.xsd` defines, then every value: numbers that
parse and fit their type, enum indexes inside their choices, and `NumElts` and `Dimsize`
that match the elements present. Each problem names its location, such as
`Cluster[pt]/I8[y]: 300 is out of range for I8 (-128..127)`. Problems in the data raise
`LVXMLError` (a `ValueError`) with the same location in its `path` attribute. Building an
impossible schema object, such as `LVEnum(())`, raises `ValueError` or `TypeError`.

`parse`, `from_lv_xml`, `from_lv_xml_all` and `validate` take `str` or `bytes`; bytes are
decoded by the encoding the XML declaration names, or as UTF-8.

## Command line

```
lvxml to-json data.xml -o data.json      # lossless tree, every name and raw value kept
lvxml to-json --values data.xml          # plain values: numbers, strings, lists, dicts
lvxml to-xml data.json -o data.xml       # tree JSON back to LabVIEW XML
lvxml validate data.xml other.xml        # check shape and values, exit 1 on any problem
echo "<I32><Name>n</Name><Val>7</Val></I32>" | lvxml to-json --values -
```

`-` reads standard input. `--encoding` sets the file encoding (default `utf-8`); if a
file is not UTF-8, name its encoding, for example `--encoding cp1252`.
`to-xml --newline lf` switches from CRLF. `--values` writes strict JSON: complex numbers
become `{"re": ..., "im": ...}` and non-finite floats the strings `"NaN"`, `"Inf"` and
`"-Inf"`. Errors go to standard error with exit status 1. `lvxml --help` lists
everything.

## What each rule rests on

Checked against the real LabVIEW file in the tests:

- The layout `dump` writes by default: the `<?xml version='1.0' standalone='yes' ?>`
  declaration, `<LVData xmlns="http://www.ni.com/LVData">`, a `<Version>` header, one
  element per line, CRLF, no indentation and no final line break.
- `DBL`, `Cluster` and one-dimensional `Array` values, and decimals written with a period.

Checked against the shipped XSD: the element structure of every type, including
multi-dimensional `Array` (repeated `<Dimsize>`), the enum `<Choice>` list and the
optional `Refnum` fields. The XSD declares the target namespace
`http://www.ni.com/labview` while the real file uses `http://www.ni.com/LVData`; the
reader accepts either, or none, keeps whichever it found, and requires every element to
share the root's namespace.

Taken from the format strings in LabVIEW 2026's run-time library (`lvrt.dll`), with no
real sample in the tests yet:

- complex values as `re +im i` (the writer's `<Val>%s +%s i</Val>`);
- only `&`, `<` and `>` escaped in text (the only entity strings beside the XML
  writer's tags are `&lt;`, `&gt;` and `&amp;`), so quotes are written as they are;
- integers and `Dimsize` as plain decimals (`%d`, `%lld`, `%llu`).

Choices `lvxml` makes where neither source settles the question:

- `Boolean` is written as `1` or `0`; the reader also accepts `true` and `false`.
- Non-finite floats are written as `NaN`, `Inf` and `-Inf` (the spellings found in the
  run-time library) and read case-insensitively.
- Floats are written with the shortest text that reads back exactly. A comma decimal
  separator raises.
- A carriage return inside a value is written as is and survives a read with `lvxml`,
  where a plain XML parser would turn it into a line feed.
- A DOCTYPE or a CDATA section is refused, nesting deeper than 100 levels raises, and an
  empty array whose shape would expand to more than 100000 nested lists raises.

## Test fixtures

The tests check the codec against ground truth from a LabVIEW 2026 installation:

- `tests/fixtures/LVXMLSchema.xsd` is the schema LabVIEW ships, copied unchanged from
  `C:\Program Files\National Instruments\LabVIEW 2026\vi.lib\Utility\LVXMLSchema.xsd`.
- `tests/fixtures/real/example-flattened-xml-file.xml` is **real LabVIEW output**,
  kept byte for byte: the file `Example Flattened XML File.xml` that LabVIEW 2026
  (version header `26.3.1f1`) wrote to `Documents\LabVIEW Data` when running the shipped
  example `examples\File IO\XML\Flatten and Unflatten XML\Flatten Data and Write to XML
  File.vi`. It holds `DBL` values and a `Cluster` with a ten-element `Array`.
- `tests/fixtures/schema/*.xml` are **schema-derived**: written by hand from the XSD to
  cover every element it defines. They are valid against the XSD, but their payloads are
  illustrative; in particular the cluster contents of the timestamp and waveform elements
  are not LabVIEW's actual internal layout, which the schema does not specify.

The real file and every schema-derived fixture are validated against the XSD with `lxml`
(a test-only dependency), parsed, decoded, and written back: the real file byte for byte,
the others canonically equal. Samples that the XSD rejects are rejected by the reader as
well. An end-to-end test installs the package and drives the installed `lvxml` command
on the real file.

## Not covered

Fixed-point `FXP` numbers and the `<Default>` and `<Attributes>` children of a variant
appear among the run-time library's writer strings but are absent from the shipped
schema, so the reader raises a clear error for them. The
timestamp and waveform elements are read as the schema describes them (a name and
clusters), not interpreted further.

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
for it.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

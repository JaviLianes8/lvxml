# lvxml guide

`lvxml` reads and writes the XML that LabVIEW's Flatten To XML function and its XML file
functions produce. This guide covers every type, the typed tree, files meant for LabVIEW,
validation, errors and the command line, then lists the evidence each rule rests on and what
changed since 0.2.

## Reading values

`from_lv_xml(text)` returns the Python value of the first value element, `from_lv_xml_all`
every value in order. Both take `str` or bytes; bytes are decoded by the encoding the XML
declaration names, or as UTF-8 (see [Files and code pages](#files-and-code-pages)).

| LabVIEW element | Python value |
| --- | --- |
| `I8` `I16` `I32` `I64` `U8` `U16` `U32` `U64` | `int`, range checked |
| `SGL` `DBL` `EXT` | `float` |
| `CSG` `CDB` `CXT` | `complex`, from `re +im i` text |
| `Boolean` | `bool`: digits, `0` is false and any other number true |
| `String` `Path` `DAQChannel` | `str` |
| `EB` `EW` `EL` enums | the selected `<Choice>` label |
| `Refnum` | its `<Val>` text |
| `Array` | `list`, nested once per `<Dimsize>`, row-major |
| `Cluster` | `dict` keyed by field name, in order |
| `LvVariant`, `Timestamp`, `WDT`, `DynamicData`, `DigitalData`, waveforms | `list` of their items' values |

```pycon
>>> from lvxml import from_lv_xml, from_lv_xml_all
>>> from_lv_xml("<CDB><Name>z</Name><Val>0.5 +-2 i</Val></CDB>")
(0.5-2j)
>>> from_lv_xml("<Boolean><Name>on</Name><Val>2</Val></Boolean>")
True
>>> from_lv_xml(
...     "<Array><Name>grid</Name><Dimsize>2</Dimsize><Dimsize>2</Dimsize>"
...     "<I32><Name></Name><Val>1</Val></I32><I32><Name></Name><Val>2</Val></I32>"
...     "<I32><Name></Name><Val>3</Val></I32><I32><Name></Name><Val>4</Val></I32></Array>"
... )
[[1, 2], [3, 4]]

```

Floats are digits with an optional sign, period and exponent, or `NaN`, `Inf`, `+Inf` and
`-Inf` in any case, with spaces around them allowed. A comma decimal separator, `Infinity`,
a signed `NaN` and an empty value raise, as they make LabVIEW 2026 refuse the value. A
cluster whose fields share a name cannot become a dict without losing data, so it raises;
read it through the typed tree instead.

Text is read the way LabVIEW reads it: only `&lt;`, `&gt;` and `&amp;` are entities, so
`&quot;`, `&#13;` or a lone `&` stay as written, carriage returns are kept, and control
characters, which LabVIEW writes raw although XML 1.0 forbids them, are read as they are.

```pycon
>>> from_lv_xml("<String><Name>s</Name><Val>a &amp; &quot;b&quot; & c</Val></String>")
'a & &quot;b&quot; & c'
>>> from_lv_xml("<String><Name>s</Name><Val>bell\x07</Val></String>")
'bell\x07'

```

## Writing values

A schema names the LabVIEW type of each value, since a Python `int` could be any width and
a `list` any element type. A scalar schema is a tag string: an integer, float or complex tag
above, `"Boolean"`, `"String"`, `"Path"` or `"DAQChannel"`. `Array(element, ndim=1)` is an
array (LabVIEW has no array of arrays), `Cluster(fields)` an ordered mapping of field name to
schema, and `LVEnum(choices, tag="EW")` an enum whose value is a label or an index. Schema
objects check themselves when built: an unknown tag raises `ValueError`, a wrong type
`TypeError`.

```pycon
>>> from lvxml import Array, Cluster, LVEnum, to_lv_xml, to_node
>>> node = to_node([[1, 2], [3, 4]], Array("U8", ndim=2), name="grid")
>>> node.dims, [item.val for item in node.items]
((2, 2), ['1', '2', '3', '4'])
>>> to_node([], Array("DBL")).items[0].val
'0.0'
>>> Array("FXP")
Traceback (most recent call last):
...
ValueError: unknown scalar tag 'FXP'

```

An empty array is written with `Dimsize` 0 and one default element, so the element type
stays visible. Booleans are written as `1` and `0`, floats with the shortest text that reads
back exactly, non-finite floats as `NaN`, `Inf` and `-Inf`, complex values as `re +im i`, and
only `&`, `<` and `>` are escaped. `to_lv_xml` returns the bare element, indented with LF line
breaks; `to_node` returns the typed tree for `dump`.

## The typed tree

`parse(text)` returns a `Document` of frozen `Node` objects that keeps everything: names, the
raw `<Val>` text, enum choices, `Dimsize`, `NumElts`, refnum fields and `<Version>` headers.
`to_value(node)` turns one node into its Python value, `dump(tree)` writes a `Document` or a
`Node` back, and `to_dict`/`from_dict` convert either to JSON-ready dicts and back.

```pycon
>>> from lvxml import Document, Node, dump, parse, to_value
>>> document = parse(
...     '<LVData xmlns="http://www.ni.com/LVData"><Version>26.3.1f1</Version>'
...     "<Refnum><Name>file</Name><RefKind>TDMS File</RefKind><Val>0x00000000</Val></Refnum>"
...     "</LVData>"
... )
>>> refnum = document.values[0]
>>> refnum.extra, to_value(refnum)
((('RefKind', 'TDMS File'),), '0x00000000')
>>> print(dump(document, newline="\n"))
<?xml version='1.0' standalone='yes' ?>
<LVData xmlns="http://www.ni.com/LVData">
<Version>26.3.1f1</Version>
<Refnum>
<Name>file</Name>
<RefKind>TDMS File</RefKind>
<Val>0x00000000</Val>
</Refnum>
</LVData>
>>> Document.from_dict(document.to_dict()) == document
True

```

`dump(tree, newline="\r\n", indent="", declaration=None)` writes LabVIEW's file layout by
default: one element per line, CRLF, no indentation, no final line break, and the
declaration for an `<LVData>` document. `newline` is CRLF, LF or CR and `indent` only spaces
and tabs. Node fields are type checked when a node is built (`TypeError`); whether they suit
the tag is checked by `dump` and `to_value` (`LVXMLError`). A refnum's `RefKind` and
`RefType` are written before `<Val>`, where LabVIEW 2026 writes them; the reader accepts them
before or after.

## Files and code pages

LabVIEW writes XML files in the system code page (cp1252 on a Western Windows) while the
declaration names no encoding. Bytes that are not UTF-8 therefore raise with a hint; decode
them with the code page and pass the text:

```pycon
>>> data = b"<String><Name>s</Name><Val>caf\xe9</Val></String>"
>>> from_lv_xml(data)
Traceback (most recent call last):
...
lvxml.LVXMLError: cannot decode byte 30 as utf-8; LabVIEW writes files in the system code page, so decode them with it (for example cp1252) and pass the text
>>> from_lv_xml(data.decode("cp1252"))
'café'

```

To write a file for LabVIEW's XML file reader, wrap the value in an `<LVData>` document with
a `Version` header (LabVIEW 2026 refuses a file without one) and encode the text with the
code page:

```pycon
>>> node = to_node({"on": True}, Cluster({"on": "Boolean"}), name="settings")
>>> text = dump(Document((Node("Version", val="26.3.1f1"), node)))
>>> text.splitlines()[:3]
["<?xml version='1.0' standalone='yes' ?>", '<LVData xmlns="http://www.ni.com/LVData">', '<Version>26.3.1f1</Version>']
>>> payload = text.encode("cp1252")

```

## Validate

`validate(text)` returns a list of problems, empty when the document is good. It first
checks the element structure `LVXMLSchema.xsd` defines, reporting one problem if that fails,
then every value: numbers that parse and fit their type, enum indexes inside their choices,
and `NumElts` and `Dimsize` that match the elements present.

```pycon
>>> from lvxml import validate
>>> validate(
...     "<Cluster><Name>pt</Name><NumElts>3</NumElts>"
...     "<I8><Name>y</Name><Val>300</Val></I8>"
...     "<EW><Name>m</Name><Choice>a</Choice><Val>4</Val></EW></Cluster>"
... )
['Cluster[pt]: cluster NumElts 3 does not match 2 elements', 'Cluster[pt]/I8[y]: 300 is out of range for I8 (-128..127)', 'Cluster[pt]/EW[m]: enum index 4 is past its 1 choices']

```

LabVIEW 2026 reads an enum index past the last choice as the last choice; `lvxml` reports it.

## Errors

| Error | When |
| --- | --- |
| `LVXMLError` (a `ValueError`) | malformed XML, a shape the schema does not allow, a value that does not parse or fit, a tree `dump` or `to_value` cannot write, bytes that do not decode |
| `ValueError` | a schema object that cannot exist (`LVEnum(())`, `Array("FXP")`), a `newline` or `indent` `dump` does not write |
| `TypeError` | input that is not `str` or bytes, a schema that is not a tag or schema object, a `Node` or `Document` field of the wrong type |

`LVXMLError.path` locates the element, such as `LVData/Cluster[pt]/DBL[x]`, and
`LVXMLError.message` says what is wrong. Values quoted in messages are cut to 40 characters
and `str()` of an error stays a few hundred characters long, so hostile input never makes a
huge message. Errors pickle with their message and path.

## Command line

`lvxml` (also `python -m lvxml`) has three commands. `to-json` writes the lossless tree, or
with `--values` plain values; `to-xml` turns tree JSON back into LabVIEW XML; `validate`
checks files. `--encoding` names the encoding of the XML files, read or written (default
UTF-8; LabVIEW's files use the system code page); JSON is always UTF-8. `-` reads standard
input. Problems go to standard error with exit status 1, usage mistakes exit with status 2.

```console
$ lvxml validate tests/fixtures/real/example-flattened-xml-file.xml
tests/fixtures/real/example-flattened-xml-file.xml: OK
$ lvxml validate tests/fixtures/labview2026/inputs/load-single-true-word.xml
tests/fixtures/labview2026/inputs/load-single-true-word.xml: LVData/Cluster[User Configuration]/Cluster[Analysis Configuration]/Boolean[Statistics]: invalid boolean value 'true', expected unsigned digits
$ lvxml to-json tests/fixtures/labview2026/save-cont-codepage.xml
lvxml: error: the file is not valid utf-8 (invalid continuation byte); try --encoding
```

`--values` writes strict JSON: complex numbers become `{"re": ..., "im": ...}` and
non-finite floats the strings `"NaN"`, `"Inf"` and `"-Inf"`. `to-xml --newline lf` switches
from CRLF.

## What each rule rests on

Checked against LabVIEW 2026 (26.3.1f1) on Windows, through files it wrote and values it
read back (`tests/fixtures/labview2026`, captured by `scripts/capture-labview-xml.ps1`):

- the file layout `dump` writes: the declaration, `<LVData xmlns="http://www.ni.com/LVData">`,
  a `<Version>` header, one element per line, CRLF, no indentation, no final line break;
- `DBL`, `String`, `Path`, `Boolean`, `EW` enums, `Cluster`, one-dimensional `Array` and a
  `Refnum` with `RefKind` written before `<Val>`, which the shipped XSD does not allow;
- escaping: only `&`, `<` and `>`, quotes and apostrophes as they are, tabs, carriage
  returns and control characters raw, text in the system code page;
- reading: only the three entities are decoded; Boolean text is digits (`2` and ` 1 ` are
  true, `true`, `TRUE` and `-1` are refused); floats as listed above; the namespace may be
  LabVIEW's, the XSD's or none, and indentation is allowed; a wrong `NumElts`, a negative
  enum index or a file without `<Version>` is refused; an index past the choices is clamped;
- `lvxml`'s own output: a file `dump` wrote with a `Version` header was read by LabVIEW
  with every value intact.

Checked against the shipped `LVXMLSchema.xsd`: the element structure of every other type,
including multi-dimensional `Array`, the enum `<Choice>` list and the optional refnum fields.
Taken from format strings in LabVIEW 2026's run-time library, with no LabVIEW sample yet:
complex values as `re +im i` and integers as plain decimals. A choice of this library where
nothing settles it: floats written with the shortest exact text (LabVIEW reads it).

## Not covered

Fixed-point `FXP` numbers and the `<Default>` and `<Attributes>` children of a variant appear
among the run-time library's writer strings but not in the shipped schema, so they raise a
clear error. Timestamp and waveform elements are read as the schema describes them (a name
and clusters), not interpreted further. The bare form `to_lv_xml` returns is what Flatten To
XML outputs; no shipped VI that unflattens a string was available to confirm LabVIEW reads it.

## Upgrading from 0.2

Every behaviour change in 1.0.0, also listed in the changelog:

1. Only `&lt;`, `&gt;` and `&amp;` are decoded; `&quot;`, `&apos;`, numeric references and a
   lone `&` are kept as written (0.2 decoded them, or raised for a lone `&`).
2. Control characters are read and written raw (0.2 raised for them).
3. `Boolean` text is unsigned digits, `0` false and any other number true; `true` and
   `false` raise (0.2 read them and raised for `2`).
4. `Infinity` in any spelling raises (0.2 read it as infinity).
5. A refnum's `RefKind` and `RefType` are read before or after `<Val>` and written before it
   (0.2 refused LabVIEW's own order and wrote them after).
6. Bytes that are not UTF-8 raise with a code page hint; `bytearray` and `memoryview` are
   read; an unknown declared encoding raises `LVXMLError` with a short message.
7. `Array`, `Cluster` and `LVEnum` check their contents when built: an unknown tag raises
   `ValueError` and a wrong type `TypeError` (0.2 raised only when writing); a non-integer
   `ndim` raises `TypeError` (was `ValueError`); `Cluster` copies its fields into a new dict.
8. `Node` and `Document` check their field types when built (`TypeError`) and store lists as
   tuples.
9. `dump` takes only CRLF, LF or CR as `newline` and spaces and tabs as `indent`, and raises
   `TypeError` for anything but a `Document` or a `Node`.
10. Messages quote at most 40 characters of a value and stay bounded; some wording changed
    (`unknown scalar tag`, `cannot decode byte N as utf-8`). Errors pickle with their message
    and path, and `LVXMLError`, `Node` and `Document` report the module `lvxml`.
11. The command line exits with status 2 for usage mistakes (was 1); `to-xml` reads its JSON
    as UTF-8 and `--encoding` only names the XML encoding; problem lines are bounded and
    characters the console cannot show are escaped; a closed output pipe ends quietly with
    status 1; `main(["--help"])` and `main(["--version"])` return 0 instead of raising
    `SystemExit`.

## Test fixtures

- `tests/fixtures/labview2026`: files LabVIEW 2026 wrote through shipped project-template
  VIs from values chosen in `scripts/make_labview_jobs.py` (labelled hand-chosen), and what
  LabVIEW read back from hand-written or `lvxml`-written inputs in `inputs/`.
- `tests/fixtures/real/example-flattened-xml-file.xml`: the file LabVIEW 2026 wrote when
  running its shipped example "Flatten Data and Write to XML File".
- `tests/fixtures/schema/*.xml`: written by hand from the XSD to cover every element it
  defines; their payloads are illustrative.
- `LVXMLSchema.xsd` belongs to NI and is not distributed: `python scripts/capture_ni.py`
  copies it from a local LabVIEW install, checked against `tests/fixtures/ni/MANIFEST.json`;
  without it the tests that validate against it skip.

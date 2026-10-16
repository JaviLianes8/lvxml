# lvxml

Read and write LabVIEW's Flatten To XML data from Python, with no LabVIEW running. Typed,
zero dependencies, Python 3.10 to 3.14.

## The problem

LabVIEW's Flatten To XML and its file writer turn any LabVIEW value into one fixed XML
shape: an element named after the data type (`DBL`, `I32`, `Boolean`, `String`, `Cluster`,
`Array`, `EW`, ...) holding a `<Name>` and a `<Val>`, or for containers their sizes and
children, usually inside an `<LVData>` file. A generic XML library parses the elements but
knows none of the conventions, and LabVIEW's reader has its own rules: it decodes only
three entities, writes control characters raw, puts a refnum's kind before its value and
writes files in the system code page. `lvxml` follows what LabVIEW 2026 actually writes and
reads, checked against files it wrote and values it read back.

## Install

```console
pip install lvxml
```

## Quick start

```pycon
>>> from lvxml import Array, Cluster, LVEnum, from_lv_xml, to_lv_xml
>>> from_lv_xml("<I32><Name>count</Name><Val>-7</Val></I32>")
-7
>>> from_lv_xml(
...     "<Cluster><Name>pt</Name><NumElts>2</NumElts>"
...     "<DBL><Name>x</Name><Val>1.5</Val></DBL>"
...     "<EW><Name>mode</Name><Choice>Idle</Choice><Choice>Run</Choice><Val>1</Val></EW>"
...     "</Cluster>"
... )
{'x': 1.5, 'mode': 'Run'}
>>> schema = Cluster({"x": "DBL", "mode": LVEnum(("Idle", "Run"))})
>>> print(to_lv_xml({"x": 1.5, "mode": "Run"}, schema, name="pt"))
<Cluster>
  <Name>pt</Name>
  <NumElts>2</NumElts>
  <DBL>
    <Name>x</Name>
    <Val>1.5</Val>
  </DBL>
  <EW>
    <Name>mode</Name>
    <Choice>Idle</Choice>
    <Choice>Run</Choice>
    <Val>1</Val>
  </EW>
</Cluster>

```

A file LabVIEW wrote is read as text in its code page and comes back byte for byte:

```pycon
>>> from lvxml import dump, parse
>>> text = (
...     "<?xml version='1.0' standalone='yes' ?>\r\n<LVData xmlns=\"http://www.ni.com/LVData\">\r\n"
...     "<Version>26.3.1f1</Version>\r\n<Boolean>\r\n<Name>on</Name>\r\n<Val>1</Val>\r\n</Boolean>\r\n"
...     "</LVData>"
... )
>>> document = parse(text)
>>> document.version, document.values[0].val
('26.3.1f1', '1')
>>> dump(document) == text
True

```

The command line converts to and from JSON and validates files:

```console
lvxml to-json --encoding cp1252 data.xml -o data.json
lvxml to-xml --encoding cp1252 data.json -o data.xml
lvxml validate data.xml
```

The [guide](https://github.com/JaviLianes8/lvxml/blob/main/GUIDE.md) covers every type, the
typed tree, validation, errors, the command line and the evidence behind each rule. Changes
are listed in the [changelog](https://github.com/JaviLianes8/lvxml/blob/main/CHANGELOG.md).

## Why

LabVIEW reads and writes this format natively, but only inside LabVIEW. On the Python side,
the LabVIEW packages on PyPI work on other things: pylabview parses LabVIEW's binary file
types, lvkit reads VIs and converts them to Python, and autolv drives a running LabVIEW.
None of them turns this XML into Python values or writes XML that LabVIEW will read back,
so that glue is usually written by hand around a generic XML parser, which gets entities,
control characters and the code page wrong for real LabVIEW files. `lvxml` is that glue,
small, typed and dependency free, tested against what LabVIEW 2026 itself writes and reads.

## License

MIT. See the [license](https://github.com/JaviLianes8/lvxml/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
